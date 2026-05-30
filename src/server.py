import subprocess
import shutil
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RawTherapee")

RT_CLI = shutil.which("rawtherapee-cli") or r"C:\Program Files\RawTherapee\rawtherapee-cli.exe"


def _run(cmd: list[str], timeout: int = 300) -> dict:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stderr": f"Timeout after {timeout}s", "stdout": "", "returncode": -1}
    except FileNotFoundError:
        return {"success": False, "stderr": f"rawtherapee-cli not found at: {RT_CLI}", "stdout": "", "returncode": -1}


@mcp.tool()
def get_version() -> str:
    """Return RawTherapee version."""
    result = _run([RT_CLI, "--version"])
    if result["success"] or result["stdout"]:
        return result["stdout"] or result["stderr"]
    return result["stderr"]


@mcp.tool()
def process_image(
    input_path: str,
    output_path: str,
    profile_path: str = "",
    output_format: str = "jpg",
    quality: int = 92,
) -> dict:
    """
    Process a RAW image with RawTherapee CLI.

    Args:
        input_path: Path to the input RAW file (e.g. .CR2, .NEF, .ARW).
        output_path: Path for the output file or directory.
        profile_path: Optional path to a .pp3 processing profile.
        output_format: Output format — 'jpg', 'png', or 'tif'. Default: 'jpg'.
        quality: JPEG quality 0-100. Default: 92.

    Returns:
        dict with success status and any output messages.
    """
    if not Path(input_path).exists():
        return {"success": False, "error": f"Input file not found: {input_path}"}

    fmt_map = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "tif": "tif", "tiff": "tif"}
    fmt = fmt_map.get(output_format.lower(), "jpg")

    cmd = [RT_CLI, "-o", output_path, f"-j{quality}" if fmt == "jpg" else f"-{fmt[0]}"]

    if profile_path:
        if not Path(profile_path).exists():
            return {"success": False, "error": f"Profile not found: {profile_path}"}
        cmd += ["-p", profile_path]

    cmd += ["-c", input_path]

    result = _run(cmd)
    if result["success"]:
        result["output_path"] = output_path
    return result


@mcp.tool()
def batch_process(
    input_dir: str,
    output_dir: str,
    profile_path: str = "",
    output_format: str = "jpg",
    quality: int = 92,
    extensions: list[str] | None = None,
) -> dict:
    """
    Batch process all RAW images in a directory.

    Args:
        input_dir: Directory containing RAW files.
        output_dir: Directory for output files.
        profile_path: Optional path to a .pp3 processing profile.
        output_format: Output format — 'jpg', 'png', or 'tif'. Default: 'jpg'.
        quality: JPEG quality 0-100. Default: 92.
        extensions: List of file extensions to process. Default: common RAW formats.

    Returns:
        dict with results per file and summary counts.
    """
    if extensions is None:
        extensions = [".cr2", ".cr3", ".nef", ".arw", ".raf", ".dng", ".orf", ".rw2", ".raw"]

    input_path = Path(input_dir)
    if not input_path.exists():
        return {"success": False, "error": f"Input directory not found: {input_dir}"}

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    files = [f for f in input_path.iterdir() if f.suffix.lower() in extensions]
    if not files:
        return {"success": False, "error": f"No RAW files found in {input_dir}"}

    results = []
    ok = 0
    failed = 0

    for f in files:
        out = str(Path(output_dir) / f.stem)
        r = process_image(str(f), out, profile_path, output_format, quality)
        results.append({"file": f.name, **r})
        if r["success"]:
            ok += 1
        else:
            failed += 1

    return {
        "success": failed == 0,
        "total": len(files),
        "processed": ok,
        "failed": failed,
        "results": results,
    }


@mcp.tool()
def list_profiles(profiles_dir: str = "") -> dict:
    """
    List available .pp3 processing profiles.

    Args:
        profiles_dir: Directory to search. Defaults to RawTherapee's built-in profiles folder.

    Returns:
        dict with list of profile paths.
    """
    search_dirs = []

    if profiles_dir:
        search_dirs.append(Path(profiles_dir))
    else:
        # Common RawTherapee profile locations on Windows
        candidates = [
            Path(r"C:\Program Files\RawTherapee\profiles"),
            Path(os.environ.get("APPDATA", "")) / "RawTherapee" / "profiles",
            Path.home() / ".config" / "RawTherapee" / "profiles",
        ]
        search_dirs = [p for p in candidates if p.exists()]

    if not search_dirs:
        return {"success": False, "error": "No profile directories found", "profiles": []}

    profiles = []
    for d in search_dirs:
        profiles.extend(str(p) for p in sorted(d.rglob("*.pp3")))

    return {"success": True, "count": len(profiles), "profiles": profiles}


@mcp.tool()
def apply_profile_and_export(
    input_path: str,
    output_path: str,
    profile_name: str,
) -> dict:
    """
    Find a built-in profile by name and apply it to export an image.

    Args:
        input_path: Path to the input RAW file.
        output_path: Path for the output file.
        profile_name: Profile name to search for (e.g. 'Default', 'Natural').

    Returns:
        dict with success status and output path.
    """
    profiles_result = list_profiles()
    if not profiles_result["success"]:
        return profiles_result

    name_lower = profile_name.lower()
    matches = [p for p in profiles_result["profiles"] if name_lower in Path(p).stem.lower()]

    if not matches:
        return {
            "success": False,
            "error": f"Profile '{profile_name}' not found",
            "available": profiles_result["profiles"],
        }

    return process_image(input_path, output_path, profile_path=matches[0])


if __name__ == "__main__":
    mcp.run()
