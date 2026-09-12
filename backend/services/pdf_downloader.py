from pathlib import Path
import requests

def download_pdf(pdf_url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(
        pdf_url,
        timeout=60,
        headers={"User-Agent": "AI-Research-Paper-Agent/1.0"}
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path
