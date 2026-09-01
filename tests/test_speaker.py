import struct
import unittest

from src.domain.speaker import _wav, build_summary


class TestSpeaker(unittest.TestCase):
    def test_build_summary_zero_tasks(self):
        """Zero tasks returns specific empty note message."""
        summary = build_summary(total=0, pending=0, watching=0, auto_classes=[])
        self.assertEqual(summary, "I did not find any tasks in that note.")

    def test_build_summary_all_pending(self):
        """All tasks pending approval."""
        summary = build_summary(total=2, pending=2, watching=0, auto_classes=[])
        self.assertEqual(summary, "I found 2 tasks. 2 tasks need your approval.")

    def test_build_summary_single_task_pending(self):
        """Singular task grammar."""
        summary = build_summary(total=1, pending=1, watching=0, auto_classes=[])
        self.assertEqual(summary, "I found 1 task. One needs your approval.")

    def test_build_summary_with_watching_and_auto_approved(self):
        """Mixed tasks with pending, watching, and auto-approved classes."""
        summary = build_summary(
            total=4, pending=1, watching=1, auto_classes=["message_person", "make_call"]
        )
        self.assertEqual(
            summary,
            "I found 4 tasks. One needs your approval, one is being watched, message person auto-approved, and make call auto-approved.",
        )

    def test_build_summary_three_auto_classes_oxford_comma(self):
        """Three auto classes joined with commas and 'and'."""
        summary = build_summary(
            total=3,
            pending=0,
            watching=0,
            auto_classes=["research", "message_person", "make_call"],
        )
        self.assertEqual(
            summary,
            "I found 3 tasks. Research auto-approved, message person auto-approved, and make call auto-approved.",
        )

    def test_wav_header_packing_format(self):
        """_wav must generate a compliant 44-byte RIFF/WAVE header for PCM audio."""
        raw_pcm = b"\x00\x01" * 100  # 200 bytes of 16-bit audio
        sample_rate = 24000
        wav_data = _wav(raw_pcm, rate=sample_rate)

        # Total size = 44 byte header + 200 bytes PCM
        self.assertEqual(len(wav_data), 244)

        # RIFF header checks
        self.assertEqual(wav_data[:4], b"RIFF")
        riff_size = struct.unpack("<I", wav_data[4:8])[0]
        self.assertEqual(riff_size, len(wav_data) - 8)

        # WAVE chunk
        self.assertEqual(wav_data[8:12], b"WAVE")
        self.assertEqual(wav_data[12:16], b"fmt ")
        fmt_size = struct.unpack("<I", wav_data[16:20])[0]
        self.assertEqual(fmt_size, 16)

        # Audio format PCM = 1, 1 channel, 24000 Hz, 16 bits
        audio_format, channels, rate, byte_rate, block_align, bits = struct.unpack(
            "<HHIIHH", wav_data[20:36]
        )
        self.assertEqual(audio_format, 1)
        self.assertEqual(channels, 1)
        self.assertEqual(rate, 24000)
        self.assertEqual(bits, 16)
        self.assertEqual(byte_rate, 24000 * 1 * 2)
        self.assertEqual(block_align, 2)

        # Data subchunk
        self.assertEqual(wav_data[36:40], b"data")
        data_size = struct.unpack("<I", wav_data[40:44])[0]
        self.assertEqual(data_size, 200)

        # Audio payload matches
        self.assertEqual(wav_data[44:], raw_pcm)


if __name__ == "__main__":
    unittest.main()
