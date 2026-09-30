"""List the FDB v1.0/v1.5 dataset folder (authors' Google Drive) without downloading."""
import gdown
fs = gdown.download_folder(
    url="https://drive.google.com/drive/folders/1DtoxMVO9_Y_nDs2peZtx3pw-U2qYgpd3",
    skip_download=True, quiet=True)
print(len(fs))
for f in fs[:60]:
    print(f.id, f.path)
