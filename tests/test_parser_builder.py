import unittest
from src.domain.intents import TaskIntent, Reversibility
from src.domain.parser import build_extraction_config

class TestParserBuilder(unittest.TestCase):
    def test_build_extraction_config_includes_all_intents(self):
        # Create a mock list of intents
        mock_intents = [
            TaskIntent(
                id="do_laundry",
                prompt_instruction="do_laundry",
                ui_label="Do Laundry",
                ui_description="Wash the clothes",
                ui_output_label="Laundry Result",
                ui_icon_name="Shirt", reversibility=Reversibility.SOFT
            ),
            TaskIntent(
                id="walk_dog",
                prompt_instruction="walk_dog",
                ui_label="Walk Dog",
                ui_description="Take dog out",
                ui_output_label="Walk Result",
                ui_icon_name="Dog", reversibility=Reversibility.SOFT
            )
        ]

        prompt, schema = build_extraction_config(mock_intents)

        # 1. Verify the prompt string explicitly names the instructions
        self.assertIn("Assign a 'class' to each task from: do_laundry, walk_dog.", prompt)
        
        # 2. Verify the JSON schema enum is strictly bound to the mock intent IDs
        class_prop = schema["properties"]["tasks"]["items"]["properties"]["class"]
        self.assertEqual(class_prop["enum"], ["do_laundry", "walk_dog"])
        
        # 3. Ensure no Vertex API call was required to verify this logic
        self.assertIsInstance(prompt, str)
        self.assertIsInstance(schema, dict)

if __name__ == '__main__':
    unittest.main()
