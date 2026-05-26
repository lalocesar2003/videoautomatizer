import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from downloaders.zip_downloader import (
    build_clip_filename,
    export_selected_assets,
    load_selected_assets,
)


SELECTED_ASSETS = {
    "project_title": "El Fin del Excel para Cobrar",
    "selected_assets": [
        {
            "scene": 1,
            "asset_type": "mixed",
            "visual_intent": "Persona frustrada usando celular.",
            "query": "person using smartphone",
            "selected_clip": {
                "provider": "pexels",
                "provider_id": "clip-1",
                "page_url": "https://pexels.com/video/clip-1",
                "preview_url": "https://videos.pexels.com/clip-1.mp4",
                "thumbnail_url": "https://images.pexels.com/clip-1.jpg",
                "duration": 10,
                "width": 1080,
                "height": 1920,
                "orientation": "vertical",
                "author_name": "Autor 1",
                "score": 95,
                "score_breakdown": {"vertical": 40},
            },
        },
        {
            "scene": 1,
            "asset_type": "mixed",
            "visual_intent": "Persona frustrada usando celular.",
            "query": "person using smartphone",
            "selected_clip": {
                "provider": "pexels",
                "provider_id": "clip-2",
                "page_url": "https://pexels.com/video/clip-2",
                "preview_url": "https://videos.pexels.com/clip-2.mp4",
                "thumbnail_url": "https://images.pexels.com/clip-2.jpg",
                "duration": 12,
                "width": 1080,
                "height": 1920,
                "orientation": "vertical",
                "author_name": "Autor 2",
                "score": 90,
                "score_breakdown": {"vertical": 40},
            },
        },
        {
            "scene": 2,
            "asset_type": "stock",
            "visual_intent": "Oficina en movimiento.",
            "query": "business office",
            "selected_clip": {
                "provider": "pexels",
                "provider_id": "clip-3",
                "page_url": "https://pexels.com/video/clip-3",
                "preview_url": "https://videos.pexels.com/clip-3.mp4",
                "thumbnail_url": "https://images.pexels.com/clip-3.jpg",
                "duration": 8,
                "width": 1080,
                "height": 1920,
                "orientation": "vertical",
                "author_name": "Autor 3",
                "score": 88,
                "score_breakdown": {"vertical": 40},
            },
        },
    ],
}


class ZipDownloaderTests(unittest.TestCase):
    def test_build_clip_filename(self) -> None:
        self.assertEqual(build_clip_filename(1, 1), "scene_01_clip_01.mp4")
        self.assertEqual(build_clip_filename(12, 3), "scene_12_clip_03.mp4")
        self.assertEqual(
            build_clip_filename(3, 1, extension=".mov"),
            "scene_03_clip_01.mov",
        )

    def test_load_selected_assets_fails_if_file_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(FileNotFoundError):
                load_selected_assets(Path(temp_dir) / "missing.json")

    def test_export_selected_assets_downloads_only_selected_and_creates_zip(self) -> None:
        calls = []

        def fake_fetcher(url: str) -> bytes:
            calls.append(url)
            return f"video-bytes:{url}".encode("utf-8")

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            clips_dir = root / "exports" / "clips"
            zip_path = root / "exports" / "selected_broll.zip"

            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(
                json.dumps(SELECTED_ASSETS, ensure_ascii=False),
                encoding="utf-8",
            )

            summary = export_selected_assets(
                selected_assets_path=selected_assets_path,
                clips_dir=clips_dir,
                zip_path=zip_path,
                fetcher=fake_fetcher,
            )

            self.assertEqual(summary["downloaded_count"], 3)
            self.assertEqual(
                calls,
                [
                    "https://videos.pexels.com/clip-1.mp4",
                    "https://videos.pexels.com/clip-2.mp4",
                    "https://videos.pexels.com/clip-3.mp4",
                ],
            )

            self.assertTrue((clips_dir / "scene_01_clip_01.mp4").exists())
            self.assertTrue((clips_dir / "scene_01_clip_02.mp4").exists())
            self.assertTrue((clips_dir / "scene_02_clip_01.mp4").exists())
            self.assertTrue(zip_path.exists())

            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    [
                        "clips/scene_01_clip_01.mp4",
                        "clips/scene_01_clip_02.mp4",
                        "clips/scene_02_clip_01.mp4",
                        "selected_assets.json",
                    ],
                )

    def test_export_selected_assets_rejects_empty_selection(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(
                json.dumps({"project_title": "Test", "selected_assets": []}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                export_selected_assets(
                    selected_assets_path=selected_assets_path,
                    clips_dir=root / "exports" / "clips",
                    zip_path=root / "exports" / "selected_broll.zip",
                    fetcher=lambda url: b"",
                )

    def test_export_selected_assets_rejects_missing_preview_url(self) -> None:
        selected_assets = {
            "project_title": "Test",
            "selected_assets": [
                {
                    "scene": 1,
                    "selected_clip": {
                        "provider": "pexels",
                        "provider_id": "clip-1",
                        "preview_url": "",
                    },
                }
            ],
        }

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(
                json.dumps(selected_assets),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                export_selected_assets(
                    selected_assets_path=selected_assets_path,
                    clips_dir=root / "exports" / "clips",
                    zip_path=root / "exports" / "selected_broll.zip",
                    fetcher=lambda url: b"",
                )

    def test_export_selected_assets_skips_manual_tasks(self) -> None:
        selected_assets = {
            "project_title": "Test",
            "selected_assets": [
                {
                    "scene": 1,
                    "selection_type": "manual_task",
                    "manual_task": {
                        "task_type": "screen_recording",
                        "status": "pending",
                    },
                },
                SELECTED_ASSETS["selected_assets"][0],
            ],
        }

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(
                json.dumps(selected_assets),
                encoding="utf-8",
            )

            summary = export_selected_assets(
                selected_assets_path=selected_assets_path,
                clips_dir=root / "exports" / "clips",
                zip_path=root / "exports" / "selected_broll.zip",
                fetcher=lambda url: b"video",
            )

            self.assertEqual(summary["downloaded_count"], 1)

    def test_export_selected_assets_copies_local_assets_without_fetching_them(self) -> None:
        calls = []

        def fake_fetcher(url: str) -> bytes:
            calls.append(url)
            return b"pexels-video"

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local_assets_dir = root / "local_assets"
            local_assets_dir.mkdir()
            local_clip_path = local_assets_dir / "dashboard.mov"
            local_clip_path.write_bytes(b"local-video")

            selected_assets = {
                "project_title": "Test",
                "selected_assets": [
                    SELECTED_ASSETS["selected_assets"][0],
                    {
                        "scene": 3,
                        "asset_type": "screen_recording",
                        "selection_type": "local",
                        "selected_clip": {
                            "provider": "local",
                            "local_path": "local_assets/dashboard.mov",
                            "original_filename": "dashboard.mov",
                        },
                    },
                ],
            }
            selected_assets_path = root / "data" / "selected_assets.json"
            clips_dir = root / "exports" / "clips"
            zip_path = root / "exports" / "selected_broll.zip"

            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(
                json.dumps(selected_assets),
                encoding="utf-8",
            )

            summary = export_selected_assets(
                selected_assets_path=selected_assets_path,
                clips_dir=clips_dir,
                zip_path=zip_path,
                fetcher=fake_fetcher,
            )

            self.assertEqual(summary["downloaded_count"], 2)
            self.assertEqual(calls, ["https://videos.pexels.com/clip-1.mp4"])
            self.assertEqual(
                (clips_dir / "scene_03_clip_01.mov").read_bytes(),
                b"local-video",
            )

            with zipfile.ZipFile(zip_path) as archive:
                self.assertIn("clips/scene_01_clip_01.mp4", archive.namelist())
                self.assertIn("clips/scene_03_clip_01.mov", archive.namelist())
                self.assertIn("selected_assets.json", archive.namelist())

    def test_export_selected_assets_rejects_local_asset_without_path(self) -> None:
        selected_assets = {
            "project_title": "Test",
            "selected_assets": [
                {
                    "scene": 3,
                    "selection_type": "local",
                    "selected_clip": {
                        "provider": "local",
                        "local_path": "",
                    },
                }
            ],
        }

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(json.dumps(selected_assets), encoding="utf-8")

            with self.assertRaises(ValueError):
                export_selected_assets(
                    selected_assets_path=selected_assets_path,
                    clips_dir=root / "exports" / "clips",
                    zip_path=root / "exports" / "selected_broll.zip",
                    fetcher=lambda url: b"",
                )

    def test_export_selected_assets_rejects_missing_local_file(self) -> None:
        selected_assets = {
            "project_title": "Test",
            "selected_assets": [
                {
                    "scene": 3,
                    "selection_type": "local",
                    "selected_clip": {
                        "provider": "local",
                        "local_path": "local_assets/missing.mp4",
                    },
                }
            ],
        }

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(json.dumps(selected_assets), encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                export_selected_assets(
                    selected_assets_path=selected_assets_path,
                    clips_dir=root / "exports" / "clips",
                    zip_path=root / "exports" / "selected_broll.zip",
                    fetcher=lambda url: b"",
                )

    def test_export_selected_assets_rejects_unsupported_local_extension(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local_assets_dir = root / "local_assets"
            local_assets_dir.mkdir()
            (local_assets_dir / "notes.txt").write_text("not video", encoding="utf-8")

            selected_assets = {
                "project_title": "Test",
                "selected_assets": [
                    {
                        "scene": 3,
                        "selection_type": "local",
                        "selected_clip": {
                            "provider": "local",
                            "local_path": "local_assets/notes.txt",
                        },
                    }
                ],
            }
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(json.dumps(selected_assets), encoding="utf-8")

            with self.assertRaises(ValueError):
                export_selected_assets(
                    selected_assets_path=selected_assets_path,
                    clips_dir=root / "exports" / "clips",
                    zip_path=root / "exports" / "selected_broll.zip",
                    fetcher=lambda url: b"",
                )

    def test_export_selected_assets_rejects_only_manual_tasks(self) -> None:
        selected_assets = {
            "project_title": "Test",
            "selected_assets": [
                {
                    "scene": 1,
                    "selection_type": "manual_task",
                    "manual_task": {
                        "task_type": "screen_recording",
                        "status": "pending",
                    },
                }
            ],
        }

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(
                json.dumps(selected_assets),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                export_selected_assets(
                    selected_assets_path=selected_assets_path,
                    clips_dir=root / "exports" / "clips",
                    zip_path=root / "exports" / "selected_broll.zip",
                    fetcher=lambda url: b"",
                )

    def test_export_selected_assets_wraps_download_errors(self) -> None:
        def failing_fetcher(url: str) -> bytes:
            raise RuntimeError("network failed")

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_assets_path = root / "data" / "selected_assets.json"
            selected_assets_path.parent.mkdir(parents=True)
            selected_assets_path.write_text(
                json.dumps(SELECTED_ASSETS),
                encoding="utf-8",
            )

            with self.assertRaises(RuntimeError):
                export_selected_assets(
                    selected_assets_path=selected_assets_path,
                    clips_dir=root / "exports" / "clips",
                    zip_path=root / "exports" / "selected_broll.zip",
                    fetcher=failing_fetcher,
                )


if __name__ == "__main__":
    unittest.main()
