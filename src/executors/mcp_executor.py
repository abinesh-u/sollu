import asyncio
import time
import hashlib

from google.genai import types
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from google.cloud import firestore

from src.domain.vertex import vertex_client
from src.executors.base import AUTO_APPROVED, EXECUTED, ExecutionResult


class McpExecutor:
    kind = "mcp_tool"
    draft_only = False
    deadline_seconds = 60

    def __init__(self, label: str, mcp_server_url: str):
        self.label = label
        self.mcp_server_url = mcp_server_url
        self.db = None

    def _get_idempotency_key(self, task: dict, tool_name: str, args: dict) -> str:
        """Hash voice_note_id + intent_id + normalized_args"""
        # correlation_id is effectively the voice_note_id
        c_id = task.get("correlation_id", "unknown_note")
        intent_id = task.get("class", "unknown_intent")
        
        # Normalize args
        args_str = str(sorted(args.items()))
        raw = f"{c_id}:{intent_id}:{tool_name}:{args_str}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _run_async(self, task: dict) -> ExecutionResult:
        if self.db is None:
            self.db = firestore.Client()
            
        t0 = time.perf_counter()
        
        async with sse_client(self.mcp_server_url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                mcp_tools = await session.list_tools()
                
                gemini_tools = []
                declarations = []
                for tool in mcp_tools.tools:
                    declarations.append(
                        types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description or "",
                            parameters=tool.input_schema
                        )
                    )
                
                if declarations:
                    gemini_tools.append(types.Tool(function_declarations=declarations))
                
                is_auto = task.get("status") == AUTO_APPROVED
                action_mode = "send directly" if is_auto else "create a draft ONLY"
                prompt = (
                    "You are a helpful assistant. Please execute the following task using the tools provided. "
                    "Output the final result of the action as a short Markdown summary.\n"
                    f"Task: {task.get('task', '')}\n"
                    f"Note: This task has {'been auto-approved' if is_auto else 'only been manually approved'}. "
                    f"If sending an email, you MUST {action_mode} (set is_draft={not is_auto})."
                )
                
                client = vertex_client()
                
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=gemini_tools if gemini_tools else None, 
                        temperature=0.0
                    )
                )
                
                if response.function_calls:
                    for fcall in response.function_calls:
                        args = fcall.args if isinstance(fcall.args, dict) else dict(fcall.args)
                        
                        # IDEMPOTENCY CHECK
                        key = self._get_idempotency_key(task, fcall.name, args)
                        doc_ref = self.db.collection("action_receipts").document(key)
                        doc = doc_ref.get()
                        
                        if doc.exists:
                            data = doc.to_dict()
                            return ExecutionResult(
                                artifact=f"Idempotent skip. Already executed `{fcall.name}`: {data.get('output_text')}",
                                status=EXECUTED,
                                tool_calls=0,
                                receipt=data,
                                elapsed_seconds=round(time.perf_counter() - t0, 2),
                            )
                        
                        # Not executed yet, call tool
                        result = await session.call_tool(
                            fcall.name, 
                            arguments=args
                        )
                        
                        output_text = "\n".join(
                            c.text for c in result.content if getattr(c, "type", "") == "text"
                        )
                        
                        receipt = {
                            "tool_name": fcall.name,
                            "args": args,
                            "output_text": output_text,
                            "timestamp": firestore.SERVER_TIMESTAMP,
                            "correlation_id": task.get("correlation_id")
                        }
                        
                        # Store receipt for idempotency
                        doc_ref.set(receipt)
                        
                        return ExecutionResult(
                            artifact=f"Executed `{fcall.name}`: {output_text}",
                            status=EXECUTED,
                            tool_calls=1,
                            receipt=receipt,
                            elapsed_seconds=round(time.perf_counter() - t0, 2),
                        )
                        
                return ExecutionResult(
                    artifact=response.text or "No action taken.",
                    status=EXECUTED,
                    tool_calls=0,
                    elapsed_seconds=round(time.perf_counter() - t0, 2),
                )

    def run(self, task: dict) -> ExecutionResult:
        return asyncio.run(self._run_async(task))
