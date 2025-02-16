import shutil, os

src = os.path.join('downloaded_files', "0.webp")
dst = os.path.join('img-news/16.02.2025_16_37_25', "0.webp")
shutil.copy2(src, dst)

files = [f for f in os.listdir('downloaded_files') if os.path.isfile(os.path.join('downloaded_files', f))]
print("Список файлів:", files)

print(os.path.isfile(os.path.join('downloaded_files', "0.webp")))
