"""Ekran yozuvi: oyna almashtirilganda (har xil o'lcham), ko'p sessiyada va juda qisqa sessiyada yozuv uzilmasin (2026-11-16).

Ikki qism: (1) `ffmpeg`/`mkvmerge` ISHLATILMAYDIGAN mantiq testlari — hamma joyda ishlaydi; (2) haqiqiy asboblar bilan
(ular o'rnatilgan va ishlaydigan joyda; aks holda o'tkazib yuboriladi).
"""
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from unittest import SkipTest
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.live import services as live
from . import transcode

T0 = datetime(2026, 11, 16, 10, 0, 0, tzinfo=dt_timezone.utc)


def tools_work() -> bool:
    try:
        for tool, flag in (('ffmpeg', '-version'), ('ffprobe', '-version'), ('mkvmerge', '--version')):
            if not shutil.which(tool) or subprocess.run([tool, flag], capture_output=True, timeout=30).returncode != 0:
                return False
        encoders = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True, timeout=30).stdout
        return 'libvpx' in encoders and 'libopus' in encoders
    except Exception:  # noqa: BLE001
        return False


class CanvasTests(SimpleTestCase):
    def test_canvas_is_the_one_of_the_biggest_session_and_stays_even(self):
        infos = [
            {'codec_name': 'vp8', 'width': 1280, 'height': 720},
            {'codec_name': 'vp8', 'width': 1101, 'height': 801},
            None,
        ]
        self.assertEqual(live._video_canvas(infos, [100, 5000, 9000]), ('vp8', 1100, 800))
        self.assertEqual(live._video_canvas(infos, [9000, 5000, 100]), ('vp8', 1280, 720))
        self.assertIsNone(live._video_canvas([None, {}]))

    def test_only_sessions_that_differ_are_re_encoded_in_order(self):
        paths = [Path(f'/x/s{i}.webm') for i in range(3)]
        infos = {
            paths[0]: {'codec_name': 'vp8', 'width': 1280, 'height': 720},
            paths[1]: {'codec_name': 'vp8', 'width': 1100, 'height': 800},
            paths[2]: {'codec_name': 'vp8', 'width': 1280, 'height': 720},
        }
        sizes = {paths[0]: 9000, paths[1]: 100, paths[2]: 8000}  # eng uzoq sessiya 1280x720
        converted = []

        def fake_conform(src, output, codec, width, height):
            converted.append((src, codec, width, height))
            return True

        with patch.object(live, '_stream_info', side_effect=lambda p, kind: infos[p]), \
                patch.object(live, '_file_size', side_effect=lambda p: sizes[p]), \
                patch.object(live, '_conform_video', side_effect=fake_conform):
            result = live._conform_video_segments(paths, Path('/tmp/t'))
        self.assertEqual(converted, [(paths[1], 'vp8', 1280, 720)])
        self.assertEqual(result[0], paths[0])
        self.assertEqual(result[2], paths[2])
        self.assertEqual(result[1], Path('/tmp/t/conformed-1.webm'))

    def test_a_failed_conversion_keeps_the_original_session(self):
        paths = [Path('/x/a.webm'), Path('/x/b.webm')]
        infos = {paths[0]: {'codec_name': 'vp8', 'width': 1280, 'height': 720},
                 paths[1]: {'codec_name': 'vp8', 'width': 640, 'height': 480}}
        with patch.object(live, '_stream_info', side_effect=lambda p, kind: infos[p]), \
                patch.object(live, '_conform_video', return_value=False):
            self.assertEqual(live._conform_video_segments(paths, Path('/tmp/t')), paths)


class TranscodeCanvasTests(SimpleTestCase):
    def probe(self, text):
        return subprocess.CompletedProcess([], 0, stdout=text, stderr='')

    def test_wide_sources_are_capped_to_1280_keeping_the_ratio(self):
        with patch.object(transcode.subprocess, 'run', return_value=self.probe('1920x1080\n')):
            self.assertEqual(transcode._canvas('a.webm'), (1280, 720))
        with patch.object(transcode.subprocess, 'run', return_value=self.probe('800x601\n')):
            self.assertEqual(transcode._canvas('a.webm'), (800, 600))

    def test_unreadable_probe_falls_back_to_the_default_canvas(self):
        with patch.object(transcode.subprocess, 'run', return_value=self.probe('video\n')):
            self.assertEqual(transcode._canvas('a.webm'), transcode.DEFAULT_CANVAS)
        with patch.object(transcode.subprocess, 'run', side_effect=OSError):
            self.assertEqual(transcode._canvas('a.webm'), transcode.DEFAULT_CANVAS)

    def test_the_output_size_is_fixed_so_a_mid_video_size_change_cannot_break_x264(self):
        with patch.object(transcode.shutil, 'which', return_value=None):
            command = transcode._command('a.webm', 'a.mp4', video=True, canvas=(1100, 800))
        vf = command[command.index('-vf') + 1]
        self.assertIn('scale=1100:800:force_original_aspect_ratio=decrease', vf)
        self.assertIn('pad=1100:800:(ow-iw)/2:(oh-ih)/2', vf)
        self.assertTrue(vf.endswith('fps=15'))
        with patch.object(transcode.shutil, 'which', return_value=None):
            audio = transcode._command('a.webm', 'a.m4a', video=False)
        self.assertNotIn('-vf', audio)



class NormalizePlanTests(SimpleTestCase):
    """`_normalize_webm` rejasi: tashlangan bo'sh sessiya, noma'lum boshlanish vaqti, ko'p sessiya. Haqiqiy asbobsiz."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        patcher = override_settings(RECORDINGS_DIR=self.tmp)
        patcher.enable()
        self.addCleanup(patcher.disable)

    def run_plan(self, count, *, starts, durations, unreadable=(), size=100):
        """Qaytaradi: `_mkv_append` ga berilgan qismlar ro'yxati (to'ldiruvchi `gap-N` va sessiya `segment-N` nomlari)."""
        raw = self.tmp / 'video.webm'
        raw.write_bytes(b'x' * (size * count))
        sessions = [{'offset': i * size, 'started_at': starts[i].isoformat() if starts[i] else None} for i in range(count)]
        captured = []

        def fake_append(parts, output):
            captured.append([p.name for p in parts])
            output.write_bytes(b'ok')
            return True

        def info(path, kind):
            number = int(path.stem.split('-')[1])
            return None if number in unreadable else {'codec_name': 'vp8', 'width': 64, 'height': 64}

        def duration(path):
            return durations[int(path.stem.split('-')[1])]

        def filler(kind, seconds, like, output):
            output.write_bytes(b'f')
            return True

        with patch.object(live, '_segment_offsets', return_value=([i * size for i in range(count)], True)), \
                patch.object(live, '_stream_info', side_effect=info), \
                patch.object(live, '_media_duration', side_effect=duration), \
                patch.object(live, '_make_filler', side_effect=filler), \
                patch.object(live, '_mkv_append', side_effect=fake_append):
            result = live._normalize_webm(raw, sessions, 'video')
        return result, captured

    def starts(self, *offsets):
        return [None if o is None else T0 + timedelta(seconds=o) for o in offsets]

    def test_twenty_sessions_are_all_kept_in_order_with_their_gaps(self):
        count = 20
        # har sessiya 5 soniya yozadi, orasida 3 soniya tanaffus
        starts = self.starts(*[i * 8 for i in range(count)])
        result, captured = self.run_plan(count, starts=starts, durations=[5.0] * count)
        self.assertTrue(result.name.endswith('-normalized.webm'))
        names = captured[0]
        self.assertEqual([n for n in names if n.startswith('segment-')], [f'segment-{i}.webm' for i in range(count)])
        self.assertEqual(len([n for n in names if n.startswith('gap-')]), count - 1)

    def test_an_empty_session_is_dropped_and_its_time_is_filled_by_the_next_gap(self):
        starts = self.starts(0, 10, 20)
        result, captured = self.run_plan(3, starts=starts, durations=[5.0, 1.0, 5.0], unreadable={1})
        names = captured[0]
        self.assertNotIn('segment-1.webm', names)
        self.assertEqual(names, ['segment-0.webm', 'gap-2.webm', 'segment-2.webm'])

    def test_unknown_start_does_not_switch_off_gap_filling_for_the_others(self):
        starts = self.starts(0, None, 30)
        result, captured = self.run_plan(3, starts=starts, durations=[5.0, 5.0, 5.0])
        names = captured[0]
        self.assertEqual(names, ['segment-0.webm', 'segment-1.webm', 'gap-2.webm', 'segment-2.webm'])

    def test_a_single_readable_session_is_returned_as_the_whole_recording(self):
        starts = self.starts(0, 10)
        result, captured = self.run_plan(2, starts=starts, durations=[5.0, 1.0], unreadable={1})
        self.assertEqual(captured, [])
        self.assertTrue(result.exists())

    def test_when_nothing_is_readable_the_raw_file_is_kept(self):
        starts = self.starts(0, 10)
        result, captured = self.run_plan(2, starts=starts, durations=[1.0, 1.0], unreadable={0, 1})
        self.assertEqual(result.name, 'video.webm')


class RealToolsTests(SimpleTestCase):
    """Haqiqiy ffmpeg/mkvmerge bilan: har xil o'lchamli sessiyalar bitta uzluksiz videoga ulanadi."""

    def setUp(self):
        if not tools_work():
            raise SkipTest('ffmpeg (libvpx/libopus) yoki mkvmerge o\'rnatilmagan / ishlamayapti')
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        patcher = override_settings(RECORDINGS_DIR=self.tmp)
        patcher.enable()
        self.addCleanup(patcher.disable)

    def make(self, name, size, seconds, color='red'):
        path = self.tmp / name
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c={color}:s={size}:r=10:d={seconds}',
            '-c:v', 'libvpx', '-g', '10', '-f', 'webm', '-live', '1', str(path),
        ], check=True, capture_output=True)
        return path

    def join(self, parts, gaps):
        raw = self.tmp / 'video.webm'
        raw.write_bytes(b''.join(p.read_bytes() for p in parts))
        offset, at, sessions = 0, 0.0, []
        for part, gap in zip(parts, gaps):
            at += gap
            sessions.append({'offset': offset, 'started_at': (T0 + timedelta(seconds=at)).isoformat()})
            offset += part.stat().st_size
            at += live._media_duration(part) or 0
        return raw, sessions

    def test_sessions_of_different_sizes_become_one_continuous_video(self):
        parts = [self.make('a.webm', '128x72', 4), self.make('b.webm', '110x80', 2, 'blue'),
                 self.make('c.webm', '128x72', 2)]
        raw, sessions = self.join(parts, [0, 3, 1])
        result = live._normalize_webm(raw, sessions, 'video')
        self.assertNotEqual(result, raw)
        duration = live._media_duration(result)
        self.assertAlmostEqual(duration, 4 + 3 + 2 + 1 + 2, delta=1.0)  # 3 ta sessiya + 2 tanaffus
        info = live._stream_info(result, 'video')
        self.assertEqual((info['width'], info['height']), (128, 72))  # eng uzoq (hajmi eng katta) sessiya kadri

    def test_twelve_short_sessions_are_all_present(self):
        parts = [self.make(f'p{i}.webm', '64x64', 1) for i in range(12)]
        raw, sessions = self.join(parts, [0] + [1] * 11)
        result = live._normalize_webm(raw, sessions, 'video')
        self.assertAlmostEqual(live._media_duration(result), 12 + 11, delta=2.0)

    def test_the_final_mp4_has_a_fixed_size_even_when_the_input_size_changes(self):
        parts = [self.make('a.webm', '128x72', 4), self.make('b.webm', '110x80', 2, 'blue')]
        raw, sessions = self.join(parts, [0, 1])
        merged = live._normalize_webm(raw, sessions, 'video')
        out = self.tmp / 'final.mp4'
        command = transcode._command(merged, out, video=True, canvas=transcode._canvas(merged))
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        info = live._stream_info(out, 'video')
        self.assertEqual((info['width'], info['height']), (128, 72))
