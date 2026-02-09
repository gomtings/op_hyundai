import os

def convert_crlf_to_lf(directory):
    extensions = {'.py', '.sh', '.cpp', '.h', '.cc', '.hpp', '.capnp', '.pyi', '.SConscript', '.ipynb'}
    for root, dirs, files in os.walk(directory):
        if '.git' in dirs:
            dirs.remove('.git')
        for file in files:
            if any(file.endswith(ext) for ext in extensions) or file == 'SConstruct' or file == 'SConscript':
                path = os.path.join(root, file)
                try:
                    with open(path, 'rb') as f:
                        content = f.read()

                    if b'\r\n' in content:
                        print(f"Converting: {path}")
                        new_content = content.replace(b'\r\n', b'\n')
                        with open(path, 'wb') as f:
                            f.write(new_content)
                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    target_dirs = [
        '.',
        'sunnypilot/modeld_v2',
        'sunnypilot/modeld',
        'sunnypilot/models',
        'selfdrive/locationd',
        'cereal',
        'selfdrive/controls',
        'system/manager'
    ]

    base_path = 'c:/GitHub/op_hyundai'
    for d in target_dirs:
        full_path = os.path.join(base_path, d)
        if os.path.exists(full_path):
            print(f"Scanning directory: {full_path}")
            convert_crlf_to_lf(full_path)
        else:
            print(f"Directory not found: {full_path}")
