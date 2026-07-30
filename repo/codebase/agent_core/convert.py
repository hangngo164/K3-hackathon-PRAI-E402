import shutil
import subprocess
from pathlib import Path
from typing import Optional


def pptx_to_pdf(input_path: Path, output_dir: Path) -> Optional[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}.pdf"
    soffice = shutil.which("soffice")
    if soffice is None:
        return None
    cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(input_path)]
    subprocess.run(cmd, check=False)
    if output_path.exists():
        return output_path
    return None
