import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Upload, Image as ImageIcon, X, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './AudioInputBar.css';

interface AudioInputBarProps {
  onProcessAudio: (audioBlob: Blob, filename: string, imageFile?: File | null) => Promise<void>;
  isProcessing: boolean;
  speakOn: boolean;
  onToggleSpeak: () => void;
}

export const AudioInputBar: React.FC<AudioInputBarProps> = ({
  onProcessAudio,
  isProcessing,
  speakOn,
  onToggleSpeak,
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
    <div className="capture-card">
      <div className="capture-header">
        <h2 className="capture-title">New voice note</h2>
        {!isRecording && !isProcessing && (
          <div className="capture-mic-badge">
            <Mic size={20} strokeWidth={2} />
          </div>
        )}
      </div>

      {isRecording && (
        <div className="recording-active-container">
          <div className="recording-status-row">
            <motion.div 
              className="waveform-canvas" 
              animate={{ width: ['0%', '100%'] }} 
              transition={{ duration: 60, ease: "linear" }} 
            />
          </div>
          <div className="recording-status-row">
            <span className="recording-timer">{formatTimer(recordSeconds)}</span>
          </div>
          <p className="capture-idle-hint">
            Listening to your instructions...
          </p>
        </div>
      )}

      {isProcessing && (
        <div className="capture-processing-row">
          <Loader2 size={24} className="animate-spin" />
          <span>Triaging note...</span>
        </div>
      )}

      {!isRecording && !isProcessing && (
        <div className="capture-body">
          <div className="capture-idle-row">
            <p className="capture-idle-hint">Try: "Text Mom I'll be late, find a good Italian place nearby, and tell me when Uber prices drop."</p>
            <div className="capture-idle-buttons">
              <button onClick={handleStartRecording} className="record-btn-primary">
                <Mic size={16} strokeWidth={2} style={{ display: 'inline', marginRight: 8 }} />
                <span>Record Note</span>
              </button>
              <span className="capture-or">or</span>
              <button onClick={() => fileInputRef.current?.click()} className="capture-add-image-btn" style={{ padding: 'var(--spacing-16) var(--spacing-32)' }}>
                <Upload size={14} strokeWidth={1.5} />
                <span>Choose voice note</span>
              </button>
            </div>
            <span className="space-hint" style={{ marginTop: 'var(--spacing-16)' }}>Hold Space to speak</span>
          </div>
        </div>
      )}

      {isRecording && (
        <div className="capture-idle-buttons" style={{ marginTop: 'var(--spacing-16)' }}>
          <button onClick={handleStopRecording} className="btn-stop-recording">
             <Square size={14} fill="currentColor" style={{ display: 'inline', marginRight: 8 }} />
             <span>Stop & Process</span>
          </button>
        </div>
      )}

      <div className="capture-footer-row">
        <input ref={fileInputRef} type="file" accept="audio/*,.wav,.mp3,.m4a,.ogg,.webm" onChange={handleFileUpload} style={{ display: 'none' }} />
        <input ref={imageInputRef} type="file" accept="image/*" onChange={handleImageSelect} style={{ display: 'none' }} />

        <div className="attachments-group">
          {imageFile ? (
            <div className="attachment-chip">
              <img src={imagePreview!} alt="attachment" />
              <span>{imageFile.name}</span>
              <button onClick={handleRemoveImage} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={12} /></button>
            </div>
          ) : (
            <button onClick={() => imageInputRef.current?.click()} disabled={isRecording || isProcessing} className="capture-add-image-btn" style={{ background: 'none', cursor: 'pointer' }}>
              <ImageIcon size={14} /> <span>Add an image</span>
            </button>
          )}
        </div>

        <div className="toggle-wrapper" role="switch" aria-checked={speakOn} tabIndex={0} onKeyDown={(e) => e.key === ' ' && onToggleSpeak()} onClick={onToggleSpeak}>
          <span>Spoken confirmation</span>
          <div className={`toggle-switch ${speakOn ? 'is-on' : ''}`}>
            <div className="toggle-thumb" />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {errorMessage && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} className="capture-error-banner">
            <AlertCircle size={16} style={{ display: 'inline', marginRight: 8 }} />
            <span>{errorMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
