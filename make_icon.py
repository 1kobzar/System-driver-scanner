from PIL import Image, ImageDraw

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

draw.rounded_rectangle([12, 12, size-12, size-12], radius=56, fill="#1E293B", outline="#3B82F6", width=10)
draw.rounded_rectangle([64, 64, size-64, size-64], radius=24, fill="#2563EB")
draw.rounded_rectangle([96, 96, size-96, size-96], radius=12, fill="#F8FAFC")

for pos in range(88, 176, 26):
    draw.rectangle([pos-6, 44, pos+6, 64], fill="#60A5FA")
    draw.rectangle([pos-6, size-64, pos+6, size-44], fill="#60A5FA")
    draw.rectangle([44, pos-6, 64, pos+6], fill="#60A5FA")
    draw.rectangle([size-64, pos-6, size-44, pos+6], fill="#60A5FA")

img.save("app_icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
print("Icon created!")
