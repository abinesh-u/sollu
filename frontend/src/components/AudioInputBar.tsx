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
        if (MediaRecorder.isTypeSupported(m)) {
          chosenMime = m;
          break;
        }
      }

      const recorder = chosenMime ? new MediaRecorder(stream, { mimeType: chosenMime }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const audioBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        const ext = recorder.mimeType.includes('mp4') ? 'm4a' : recorder.mimeType.includes('ogg') ? 'ogg' : 'webm';
        await onProcessAudio(audioBlob, `recording.${ext}`, imageFile);
      };

      recorder.start(250);
      setIsRecording(true);
      setRecordSeconds(0);

      timerRef.current = window.setInterval(() => {
        setRecordSeconds((s) => s + 1);
      }, 1000);
    } catch (err: any) {
      setErrorMessage(
        err.name === 'NotAllowedError'
          ? 'Microphone permission denied. Please allow microphone access.'
          : `Recording failed: ${err.message || err}`
      );
      setIsRecording(false);
    }
  };

  const handleStopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
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
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full">
      {/* Paper White Container Card with 16px radius */}
      <div className="bg-[#fcfcfc] rounded-[16px] p-6">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          
          {/* Left: Headline and Eyebrow */}
          <div className="flex-1 space-y-1.5">
            <span className="text-[12px] font-medium tracking-[0.06em] uppercase text-[#043f2e]/80 block">
              Autonomous Voice Errand Intake
            </span>
            <h2 className="text-2xl sm:text-3xl font-serif text-[#043f2e] tracking-[-0.72px] leading-tight">
              Speak or upload your errand note
            </h2>
            <p className="text-sm text-[#242423] leading-relaxed max-w-[65ch]">
              Tasks are decomposed into <span className="font-medium text-[#043f2e]">now</span>, <span className="font-medium text-[#043f2e]">next</span>, and <span className="font-medium text-[#043f2e]">later</span> lanes. Autonomy is earned through consecutive approvals on the trust ladder.
            </p>

            {/* Image Preview */}
            <AnimatePresence>
              {imagePreview && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex items-center gap-2 pt-2"
                >
                  <div className="rounded-[4px] border border-[#043f2e]/20 bg-[#eef2e3] p-1.5 flex items-center gap-2">
                    <img
                      src={imagePreview}
                      alt="Attachment Preview"
                      className="w-7 h-7 rounded-[2px] object-cover"
                    />
                    <span className="text-xs font-mono text-[#043f2e] pr-1 truncate max-w-[180px]">
                      {imageFile?.name}
                    </span>
                    <button
                      onClick={handleRemoveImage}
                      className="text-[#043f2e]/60 hover:text-[#7a2e1e] transition-colors cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right: Controls & Actions */}
          <div className="flex flex-wrap items-center gap-3">
            
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,.wav,.mp3,.m4a,.ogg,.webm"
              onChange={handleFileUpload}
              className="hidden"
            />
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageSelect}
              className="hidden"
            />

            {/* Attach Image Button */}
            {!imageFile && (
              <button
                onClick={() => imageInputRef.current?.click()}
                disabled={isRecording || isProcessing}
                className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-[4px] border border-[#043f2e]/25 hover:bg-[#eef2e3] text-xs font-medium text-[#043f2e] transition-all disabled:opacity-50 cursor-pointer"
              >
                <ImageIcon className="w-4 h-4 text-[#043f2e]" />
                <span>Attach Photo</span>
              </button>
            )}

            {/* Upload Audio Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isRecording || isProcessing}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-[4px] border border-[#043f2e]/25 hover:bg-[#eef2e3] text-xs font-medium text-[#043f2e] transition-all disabled:opacity-50 cursor-pointer"
            >
              <Upload className="w-4 h-4 text-[#043f2e]" />
              <span>Upload Audio</span>
            </button>

            {/* Primary Action Button (Chartreuse #c8f169) */}
            {isRecording ? (
              <button
                onClick={handleStopRecording}
                className="flex items-center gap-2 px-5 py-2.5 rounded-[4px] bg-[#7a2e1e] hover:bg-[#632417] text-[#fcfcfc] text-xs font-medium transition-all cursor-pointer"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span className="font-mono">{formatTimer(recordSeconds)}</span>
                <span>Stop & Triage</span>
              </button>
            ) : (
              <button
                onClick={handleStartRecording}
                disabled={isProcessing}
                className="flex items-center gap-2 px-5 py-2.5 rounded-[4px] bg-[#c8f169] hover:bg-[#bde85b] text-[#000000] text-xs font-medium transition-all disabled:opacity-50 cursor-pointer"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-[#000000]" />
                    <span>Triaging Note...</span>
                  </>
                ) : (
                  <>
                    <Mic className="w-4 h-4 text-[#000000]" />
                    <span>Record Note</span>
                  </>
                )}
              </button>
            )}

          </div>
        </div>

        {/* Recording Visualizer Bar */}
        <AnimatePresence>
          {isRecording && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="mt-4 pt-3 border-t border-[#043f2e]/10 flex items-center justify-between"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#7a2e1e] animate-pulse" />
                <span className="text-xs font-mono text-[#7a2e1e] font-medium">Recording microphone stream...</span>
              </div>
              <div className="flex items-center gap-1">
                {[30, 60, 90, 50, 80, 40, 90, 60, 30].map((h, i) => (
                  <motion.div
                    key={i}
                    animate={{ height: [6, h * 0.25, 6] }}
                    transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.08 }}
                    className="w-1 bg-[#7a2e1e] rounded-full"
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error Alert */}
        <AnimatePresence>
          {errorMessage && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="mt-4 p-3 rounded-[4px] bg-[#f0e2dd] border border-[#7a2e1e]/20 text-[#7a2e1e] text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
};
