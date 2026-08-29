import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Upload, Image as ImageIcon, X, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface AudioInputBarProps {
  onProcessAudio: (audioBlob: Blob, filename: string, imageFile?: File | null) => Promise<void>;
  isProcessing: boolean;
}

export const AudioInputBar: React.FC<AudioInputBarProps> = ({
  onProcessAudio,
  isProcessing,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const handleStartRecording = async () => {
    setErrorMessage(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
      let chosenMime = '';
      for (const m of mimeTypes) {
        if (MediaRecorder.isTypeSupported(m)) { chosenMime = m; break; }
      }
      const recorder = chosenMime ? new MediaRecorder(stream, { mimeType: chosenMime }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        const ext = recorder.mimeType.includes('mp4') ? 'm4a' : recorder.mimeType.includes('ogg') ? 'ogg' : 'webm';
        await onProcessAudio(audioBlob, `recording.${ext}`, imageFile);
      };

      recorder.start(250);
      setIsRecording(true);
      setRecordSeconds(0);
      timerRef.current = window.setInterval(() => setRecordSeconds((s) => s + 1), 1000);
    } catch (err: any) {
      setErrorMessage('Microphone access denied or error occurred.');
      setIsRecording(false);
    }
  };

  const handleStopRecording = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErrorMessage(null);
    await onProcessAudio(file, file.name, imageFile);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleRemoveImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImageFile(null);
    setImagePreview(null);
    if (imageInputRef.current) imageInputRef.current.value = '';
  };

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full">
      {/* Paper White Elevated Card - Vertical layout */}
      <div className="bg-[#fcfcfc] rounded-[16px] p-8 shadow-[0_8px_30px_rgba(4,63,46,0.08)] relative overflow-hidden">
        
        {/* Header Row */}
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-sans font-semibold text-[#043f2e]">New voice note</h2>
          {!isRecording && !isProcessing && (
            <div className="w-10 h-10 rounded-full bg-[#c8f169] flex items-center justify-center border border-[#043f2e]/10">
              <Mic className="w-5 h-5 text-[#043f2e]" />
            </div>
          )}
        </div>

        {/* Recording Visualizer */}
        {isRecording && (
          <div className="mb-8">
            <div className="h-1.5 w-full bg-[#043f2e]/10 rounded-full overflow-hidden mb-4">
              <motion.div 
                className="h-full bg-[#043f2e]" 
                animate={{ width: ['0%', '100%'] }} 
                transition={{ duration: 60, ease: "linear" }} 
              />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-lg font-mono text-[#043f2e]">{formatTimer(recordSeconds)}</span>
              <div className="flex-1 flex items-center gap-1 overflow-hidden h-8">
                {[...Array(24)].map((_, i) => (
                  <motion.div
                    key={i}
                    animate={{ height: [8, Math.random() * 24 + 8, 8] }}
                    transition={{ repeat: Infinity, duration: 0.5 + Math.random() * 0.5 }}
                    className="w-1 bg-[#043f2e]/20 rounded-full"
                  />
                ))}
              </div>
            </div>
            <p className="mt-4 text-[#242423] font-sans leading-relaxed text-sm h-12">
              Listening to your instructions...
            </p>
          </div>
        )}

        {/* Processing State */}
        {isProcessing && (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-[#043f2e] mb-4" />
            <span className="text-[#043f2e] font-medium text-sm">Triaging note...</span>
          </div>
        )}

        {/* Default State (Idle) */}
        {!isRecording && !isProcessing && (
          <div className="py-6 flex flex-col items-center gap-4">
             <p className="text-sm text-[#043f2e]/60 text-center mb-4">
               Ready to record. Click the button below to start speaking.
             </p>
             <div className="flex flex-col sm:flex-row items-center gap-4">
               <button
                 onClick={handleStartRecording}
                 className="flex items-center gap-2 px-6 py-3 rounded-[4px] bg-[#c8f169] text-[#000000] font-medium transition-all hover:bg-[#bde85b] hover:shadow-[0_4px_12px_rgba(200,241,105,0.4)] cursor-pointer"
               >
                 <Mic className="w-5 h-5" />
                 <span>Record Note</span>
               </button>
               <span className="text-[#043f2e]/40 text-xs">or</span>
               <button
                 onClick={() => fileInputRef.current?.click()}
                 className="flex items-center gap-2 px-6 py-3 rounded-[4px] bg-transparent border border-[#043f2e]/25 text-[#043f2e] font-medium transition-all hover:bg-[#eef2e3] cursor-pointer"
               >
                 <Upload className="w-4 h-4" />
                 <span>Choose voice note</span>
               </button>
             </div>
          </div>
        )}

        {/* Stop Button (Active) */}
        {isRecording && (
          <div className="flex justify-center mt-4">
            <button
              onClick={handleStopRecording}
              className="flex items-center gap-2 px-6 py-3 rounded-[4px] bg-[#7a2e1e] text-[#fcfcfc] font-medium transition-all hover:bg-[#632417] cursor-pointer"
            >
               <Square className="w-4 h-4 fill-current" />
               <span>Stop & Process</span>
            </button>
          </div>
        )}

        {/* Attachments & Toggles */}
        <div className="mt-8 pt-4 border-t border-[#043f2e]/10 flex items-center justify-between gap-2 flex-wrap">
          
          <input ref={fileInputRef} type="file" accept="audio/*,.wav,.mp3,.m4a,.ogg,.webm" onChange={handleFileUpload} className="hidden" />
          <input ref={imageInputRef} type="file" accept="image/*" onChange={handleImageSelect} className="hidden" />

          {/* Attachment Preview or Add button */}
          {imageFile ? (
            <div className="rounded-[4px] bg-[#eef2e3] p-1 flex items-center gap-2 max-w-[200px]">
              <img src={imagePreview!} className="w-6 h-6 rounded-[2px] object-cover" />
              <span className="text-[10px] font-mono text-[#043f2e] truncate">{imageFile.name}</span>
              <button onClick={handleRemoveImage} className="text-[#7a2e1e] hover:text-[#632417] px-1 cursor-pointer"><X className="w-3 h-3" /></button>
            </div>
          ) : (
            <button
              onClick={() => imageInputRef.current?.click()}
              disabled={isRecording || isProcessing}
              className="flex items-center gap-1.5 text-xs font-medium text-[#043f2e]/60 hover:text-[#043f2e] transition-colors cursor-pointer"
            >
              <ImageIcon className="w-4 h-4" /> <span>Add an image</span>
            </button>
          )}

          {/* Spoken summary toggle */}
          <div className="flex items-center gap-2 text-xs font-medium text-[#043f2e]/80">
            <span>Spoken summary</span>
            <div className="w-8 h-4 bg-[#c8f169] rounded-full relative shadow-[inset_0_1px_3px_rgba(0,0,0,0.1)]">
              <div className="w-3 h-3 bg-white rounded-full absolute right-0.5 top-0.5 shadow-sm" />
            </div>
          </div>
        </div>

        {/* Error Alert */}
        <AnimatePresence>
          {errorMessage && (
            <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} className="absolute top-4 left-4 right-4 p-3 rounded-[8px] bg-[#f0e2dd] border border-[#7a2e1e]/20 text-[#7a2e1e] text-xs flex items-center gap-2 shadow-lg">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
};
