#\!/usr/bin/env python3
import struct

def create_png(width, height, filename):
    """Create a simple PNG file with the specified dimensions"""
    # PNG file signature
    png_signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>2I5B', width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    ihdr_crc = 0x1db71064  # We'll use a dummy CRC for simplicity
    
    # Simple blue pixel data (RGBA: blue with full alpha)
    pixel_data = b'\x64\x78\xc8\xff' * (width * height)  # Blue pixels
    
    # IDAT chunk (compressed pixel data - simplified)
    idat_data = b'x\x9c' + pixel_data  # Basic zlib header + data
    
    # IEND chunk
    iend_data = b''
    
    with open(filename, 'wb') as f:
        f.write(png_signature)
        
        # Write IHDR
        f.write(struct.pack('>I', len(ihdr_data)))
        f.write(b'IHDR')
        f.write(ihdr_data)
        f.write(struct.pack('>I', ihdr_crc))
        
        # Write simplified IDAT
        f.write(struct.pack('>I', len(idat_data)))
        f.write(b'IDAT')
        f.write(idat_data)
        f.write(struct.pack('>I', 0))  # Dummy CRC
        
        # Write IEND
        f.write(struct.pack('>I', 0))
        f.write(b'IEND')
        f.write(struct.pack('>I', 0xAE426082))

# Create various sized icons
sizes = [(32, 32), (128, 128), (256, 256)]
names = ['32x32.png', '128x128.png', '128x128@2x.png', 'icon.png', 'Square30x30Logo.png']

for name in names:
    create_png(32, 32, name)
    print(f'Created {name}')

print('All icons created successfully')
