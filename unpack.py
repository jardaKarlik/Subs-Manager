import json
import base64
import zlib
import os
import sys

def unpack_bundler_html(html_path, out_dir):
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Find the manifest tag
    start_tag = '<script type="__bundler/manifest">'
    end_tag = '</script>'
    
    start_idx = html_content.find(start_tag)
    if start_idx == -1:
        print("Manifest not found.")
        return
        
    start_idx += len(start_tag)
    end_idx = html_content.find(end_tag, start_idx)
    
    manifest_json = html_content[start_idx:end_idx].strip()
    
    try:
        manifest = json.loads(manifest_json)
    except json.JSONDecodeError as e:
        print(f"Failed to parse manifest JSON: {e}")
        return

    os.makedirs(out_dir, exist_ok=True)
    
    for uuid, entry in manifest.items():
        mime = entry.get('mime', '')
        compressed = entry.get('compressed', False)
        data_b64 = entry.get('data', '')
        
        try:
            # Decode base64
            data_bytes = base64.b64decode(data_b64)
            
            # Decompress if needed
            if compressed:
                try:
                    # The JS uses DecompressionStream('gzip'), so it's gzip compressed
                    # zlib.decompress with wbits=31 handles gzip
                    data_bytes = zlib.decompress(data_bytes, 31)
                except Exception as e:
                    print(f"Warning: Failed to decompress {uuid}: {e}")
            
            # Determine extension
            ext = '.bin'
            if mime == 'text/javascript' or mime == 'application/javascript':
                ext = '.js'
            elif mime == 'text/babel' or mime == 'text/jsx':
                ext = '.jsx'
            elif mime == 'text/css':
                ext = '.css'
            elif mime == 'image/svg+xml':
                ext = '.svg'
            elif mime == 'text/html':
                ext = '.html'
            
            # Since we don't have original filenames, we'll just save by uuid
            # We'll also see if there's a template script to reconstruct the main HTML
            out_file = os.path.join(out_dir, f"{uuid}{ext}")
            
            # If it's text, write as string, else binary
            if 'text/' in mime or 'application/javascript' in mime or 'image/svg' in mime:
                with open(out_file, 'w', encoding='utf-8') as out_f:
                    out_f.write(data_bytes.decode('utf-8'))
            else:
                with open(out_file, 'wb') as out_f:
                    out_f.write(data_bytes)
                    
            print(f"Extracted {uuid}{ext} ({mime})")
            
        except Exception as e:
            print(f"Failed to extract {uuid}: {e}")

    # Now let's try to extract the template and replace UUIDs with local paths
    template_start_tag = '<script type="__bundler/template">'
    t_start_idx = html_content.find(template_start_tag)
    if t_start_idx != -1:
        t_start_idx += len(template_start_tag)
        t_end_idx = html_content.find(end_tag, t_start_idx)
        template_json = html_content[t_start_idx:t_end_idx].strip()
        
        try:
            template = json.loads(template_json)
            
            # Replace UUIDs with local filenames
            for uuid, entry in manifest.items():
                mime = entry.get('mime', '')
                ext = '.bin'
                if mime == 'text/javascript' or mime == 'application/javascript':
                    ext = '.js'
                elif mime == 'text/babel' or mime == 'text/jsx':
                    ext = '.jsx'
                elif mime == 'text/css':
                    ext = '.css'
                elif mime == 'image/svg+xml':
                    ext = '.svg'
                elif mime == 'text/html':
                    ext = '.html'
                    
                local_path = f"{uuid}{ext}"
                template = template.replace(uuid, local_path)
            
            # Remove integrity and crossorigin attributes as the bundler script does
            import re
            template = re.sub(r'\s+integrity="[^"]*"', '', template, flags=re.IGNORECASE)
            template = re.sub(r'\s+crossorigin="[^"]*"', '', template, flags=re.IGNORECASE)
            
            with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(template)
            print("Extracted and reconstructed index.html")
            
        except Exception as e:
            print(f"Failed to process template: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python unpack.py <html_file> <out_dir>")
        sys.exit(1)
    unpack_bundler_html(sys.argv[1], sys.argv[2])
