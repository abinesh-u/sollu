import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Upload, Image as ImageIcon, X, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './AudioInputBar.css';

interface AudioInputBarProps {
  onProcessAudio: (audioBlob: Blob | null, filename: string, imageFile?: File | null, text?: string) => Promise<void>;
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
  const [transcript, setTranscript] = useState<string>('');
  const [isReviewing, setIsReviewing] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedMime, setRecordedMime] = useState<string>('');
  const recognitionRef = useRef<any>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Audio Visualizer Refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === ' ' && !e.repeat) {
        // Ignore if user is typing in an input or focused on a button/toggle
        if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLButtonElement) {
          return;
        }
        // Also ignore if focused on the toggle wrapper
        if ((e.target as HTMLElement).closest('.toggle-wrapper')) {
          return;
        }
        e.preventDefault();
        if (!isRecording && !isProcessing && !isReviewing) {
          handleStartRecording();
        }
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === ' ') {
        if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLButtonElement) {
          return;
        }
        if ((e.target as HTMLElement).closest('.toggle-wrapper')) {
          return;
        }
        e.preventDefault();
        if (isRecording) {
          handleStopRecording();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [isRecording, isProcessing, isReviewing]);

  const drawVisualizer = () => {
    if (!canvasRef.current || !analyserRef.current || !dataArrayRef.current) return;
    
    const canvas = canvasRef.current;
    const canvasCtx = canvas.getContext('2d');
    if (!canvasCtx) return;

    const width = canvas.width;
    const height = canvas.height;
    
    const dataArray = dataArrayRef.current as any;
    analyserRef.current.getByteFrequencyData(dataArray);
    
    canvasCtx.clearRect(0, 0, width, height);
    
    const barWidth = (width / dataArrayRef.current.length) * 2.5;
    let x = 0;
    
    for (let i = 0; i < dataArrayRef.current.length; i++) {
      const barHeight = (dataArrayRef.current[i] / 255) * height;
      
      canvasCtx.fillStyle = '#1a1a1a';
      canvasCtx.fillRect(x, height - barHeight, barWidth, barHeight);
      
      x += barWidth + 1;
    }
    
    animationFrameRef.current = requestAnimationFrame(drawVisualizer);
  };

  useEffect(() => {
    if (isRecording) {
      // The canvas is now in the DOM. Start drawing.
      drawVisualizer();
    } else {
      // Clean up if it stops
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    }
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [isRecording]);

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

      // Set up Audio Visualizer
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
      
      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;
      sourceRef.current = source;
      dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);
      
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        const ext = recorder.mimeType.includes('mp4') ? 'm4a' : recorder.mimeType.includes('ogg') ? 'ogg' : 'webm';
        setRecordedBlob(audioBlob);
        setRecordedMime(`recording.${ext}`);
        setIsReviewing(true);
      };

      setTranscript('');
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          
          recognition.onresult = (event: any) => {
            let currentTranscript = '';
            for (let i = 0; i < event.results.length; i++) {
              currentTranscript += event.results[i][0].transcript;
            }
            setTranscript(currentTranscript);
          };
          
          recognition.start();
          recognitionRef.current = recognition;
        } catch (e) {
          console.warn('SpeechRecognition error:', e);
        }
      }

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
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    
    setIsRecording(false);
  };
  const handleSubmitReview = async () => {
    setIsReviewing(false);
    if (recordedBlob && transcript.trim()) {
      // Send text and audio
      await onProcessAudio(recordedBlob, recordedMime, imageFile, transcript);
    } else if (recordedBlob) {
      await onProcessAudio(recordedBlob, recordedMime, imageFile);
    } else if (transcript.trim()) {
      await onProcessAudio(null, 'text.txt', imageFile, transcript);
    }
    setRecordedBlob(null);
    setTranscript('');
  };

  const handleDiscardReview = () => {
    setIsReviewing(false);
    setRecordedBlob(null);
    setTranscript('');
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
        {isRecording && (
          <div className="capture-mic-badge recording-pulse">
            <Mic size={20} strokeWidth={2} color="#ff4444" />
          </div>
        )}
      </div>

      {isRecording && (
        <div className="recording-active-container">
          <div className="recording-status-row">
            <canvas 
              ref={canvasRef}
              className="waveform-canvas" 
              width={200}
              height={40}
              style={{ width: '100%', height: '40px', background: 'transparent' }}
            />
          </div>
          <div className="recording-status-row">
            <span className="recording-timer">{formatTimer(recordSeconds)}</span>
          </div>
          <p className="capture-idle-hint" style={{ fontStyle: transcript ? 'normal' : 'italic', minHeight: '1.5em' }}>
            {transcript || 'Listening to your instructions...'}
          </p>
        </div>
      )}

      {isProcessing && (
        <div className="capture-processing-row">
          <Loader2 size={24} className="animate-spin" />
          <span>Triaging note...</span>
        </div>
      )}

      {isReviewing && !isProcessing && (
        <div className="capture-body">
          <div className="capture-idle-row" style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
            <textarea
              autoFocus
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmitReview();
                } else if (e.key === 'Escape') {
                  e.preventDefault();
                  handleDiscardReview();
                }
              }}
              className="transcript-edit-area"
              placeholder="Edit your voice note here..."
              style={{
                width: '100%',
                minHeight: '80px',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--color-fog)',
                marginBottom: '16px',
                fontFamily: 'inherit',
                fontSize: 'var(--text-body-sm)'
              }}
            />
            <div className="capture-idle-buttons" style={{ width: '100%', justifyContent: 'space-between' }}>
              <button onClick={handleDiscardReview} className="capture-add-image-btn" style={{ padding: '8px 16px', color: 'red' }}>
                <X size={14} style={{ display: 'inline', marginRight: 4 }} />
                Discard
              </button>
              <button onClick={handleSubmitReview} className="record-btn-primary" style={{ padding: '8px 24px' }}>
                <span>Send to Sollu</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {!isRecording && !isProcessing && !isReviewing && (
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
