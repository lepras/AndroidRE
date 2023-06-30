import subprocess
import sys
import socket
import importlib
import re
import time
import platform

def welcome():
    welcome_message = "welcome to libpatcher"
    print(welcome_message)

def check_radare2_installed():
    try:
        subprocess.check_output(['r2', '-v'], stderr=subprocess.STDOUT)
    except Exception as e:
        print("\n\033[1;31mradare2 is not installed. Program terminated.\nEnter this command for installing radare2\033[0m\n`pkg install radare2 -y`\n\033[1;31mOr go to\033[0m\n`https://github.com/radareorg/radare2`")
        sys.exit(1)

def check_internet_connection():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except socket.error:
        return False

def install_r2pipe():
    try:
        importlib.import_module("pip").main(["install", "r2pipe"])
        print("\n\033[1;32mr2pipe installation complete.\033[0m")
        import r2pipe
    except Exception as e:
        print(f"\n\033[1;31mFailed to install r2pipe: {str(e)}\033[0m")
        sys.exit(1)

def check_r2pipe_installed():
    try:
        import r2pipe
    except ImportError:
        print("\n\033[1;31mr2pipe is not installed.\033[0m")
        response = input("\n\033[1;33mDo you want to install r2pipe? (y/n): \033[0m")
        if response.lower() == "y":
            if check_internet_connection():
                global r2pipe
                r2pipe = install_r2pipe()
            else:
                print("\n\033[1;31mNo internet connection. Cannot install r2pipe. Program terminated.\033[0m")
                sys.exit(1)
        else:
            print("\n\033[1;31mr2pipe installation skipped.\nProgram terminated.\033[0m")
            sys.exit()

def prompt_file_path():
    global file_path
    print("\n\033[1;36m// Remember, arm64-v8a and armeabi-v7a are acceptable.\033[0m")
    file_path = input("\n\033[1;33mEnter executable path: \033[0m")
    while not file_path:
        print("\033[1;31mFile path empty.\033[0m")
        file_path = input("\n\033[1;33mEnter executable path (or 'x' to terminate): \033[0m")
        if file_path.lower() == 'x':
            print("\n\033[1;31mProgram terminated by user.\033[0m")
            sys.exit()

def check_file_architecture(file_path):
    try:
        r2 = r2pipe.open(file_path)
        info_json = r2.cmdj("ij")
        arch = info_json.get("bin", {}).get("machine", "")
        r2.quit()
        if not arch:
            print("\033[1;31mFile is not executable.\033[0m")
            return None
        else:
            return arch
    except Exception as e:
        print(f"\n\033[1;31mAn error occurred while reading the file: {str(e)}\033[0m")
        return None

def print_architecture():
    global detected_arch
    while True:
        detected_arch = check_file_architecture(file_path)

        if detected_arch is not None and "aarch64" in detected_arch:
            print("\n\033[1;32mDetected architecture: arm64-v8a\nPatches of arm64 will be applied.\033[0m")
            break  # Skip to the next iteration of the while loop
        elif detected_arch is not None and "ARM" in detected_arch:
            print("\n\033[1;32mDetected architecture: armeabi-v7a\nPatches of arm32 will be applied.\033[0m")
            break  # Skip to the next iteration of the while loop
        elif detected_arch is not None and ("x86-64" in detected_arch or "Intel" in detected_arch or "MIPS" in detected_arch):
            print("\n\033[1;31mDetected architecture:", detected_arch, "\nPatches are not available.\033[0m")
            prompt_file_path()
        elif detected_arch is None:
            print("\033[1;31mInvalid file path.\033[0m")
            prompt_file_path()

def validate_offsets(offsets):
    if not offsets:
        return True
    pattern = r"^0x[0-9a-fA-F]+$"
    offset_list = offsets.split(",")
    for offset in offset_list:
        if not re.match(pattern, offset.strip()):
            return False
    return True

def prompt_offsets(offset_type):
    offsets = input(f"\033[1;33mEnter offsets for {offset_type}: \033[0m")
    while not validate_offsets(offsets):
        print("\033[1;31mInvalid offsets format. Please enter valid offsets.\033[0m")
        offsets = input(f"\n\033[1;33mEnter offsets for {offset_type}:\033[0m\033[90m(e.g. 0x100 or 0x100,0x200)\033[0m")
    return offsets

def prompt_all_offset_types():
    print("\n\033[1;36m// Leave empty if not necessary.\n// Separate by commas if there are multiple offsets.\033[0m\n")
    global offsets
    offsets = {}
    offset_types = [
        "boolean_true",
        "boolean_false",
        "integer_zero",
        "integer16_max",
        "integer32_max",
        "long_zero",
        "long_64",
        "float_zero",
        "double_zero",
        "void_nop",
    ]
    for offset_type in offset_types:
        offsets[offset_type] = prompt_offsets(offset_type)
    return offsets

def set_value_at_offset(r2, offset, data_type, value, detected_arch):
    r2.cmd(f"wx {value} @ {offset}")
    print(f"\033[1;32mValue of {data_type} has been set at offset {offset}.\033[0m")

def set_values_to_offsets(file_path, offsets):
    start_time = time.time()
    r2 = r2pipe.open(file_path)
    r2.cmd("oo+")

    for data_type, offset_list in offsets.items():
        if offset_list:
            for offset in offset_list.split(","):
                value = get_value_by_data_type(data_type, detected_arch)
                if value is None:
                    print(f"\n\033[1;31mInvalid data type: {data_type}. Skipping offset {offset}.\033[0m")
                    continue

                set_value_at_offset(r2, offset.strip(), data_type, value, detected_arch)

    r2.quit()
    elapsed_time = time.time() - start_time
    print(f"\n\033[1;32mFinished setting values. Elapsed time: {elapsed_time:.2f} seconds.\033[0m")

def get_value_by_data_type(data_type, detected_arch):
    if data_type == "boolean_true":
        return "20008052C0035FD6" if detected_arch.endswith("aarch64") else "0100A0E31EFF2FE1"
    elif data_type == "boolean_false":
        return "00008052C0035FD6" if detected_arch.endswith("aarch64") else "0000A0E31EFF2FE1"
    elif data_type == "integer_zero":
        return "00008052C0035FD6" if detected_arch.endswith("aarch64") else "0000A0E31EFF2FE1"
    elif data_type == "integer16_max":
        return "E0FF8F52C0035FD6" if detected_arch.endswith("aarch64") else "FF0F07E31EFF2FE1"
    elif data_type == "integer32_max":
        return "E0FF9F52E0FFAF72C0035FD6" if detected_arch.endswith("aarch64") else "FF0F0FE3FF0F47E31EFF2FE1"
    elif data_type == "long_zero":
        return "00008052C0035FD6" if detected_arch.endswith("aarch64") else "0000A0E31EFF2FE1"
    elif data_type == "long_64":
        return "E0FF9FD2E0FFBFF2E00FC0F2C0035FD6" if detected_arch.endswith("aarch64") else "0201E0E31EFF2FE1"
    elif data_type == "float_zero":
        return "E003271EC0035FD6" if detected_arch.endswith("aarch64") else "0000A0E31EFF2FE1"
    elif data_type == "double_zero":
        return "E003679EC0035FD6" if detected_arch.endswith("aarch64") else "0000A0E31EFF2FE1"
    elif data_type == "void_nop":
        return "C0035FD6" if detected_arch.endswith("aarch64") else "A0E31EFF2FE1"
    else:
        return None

def prompt_open_link():
    message = "\n\033[1mHappy reversing!\nDon't forget to visit TDOhex.\nWe are trying to provide useful knowledge and ways to understand patching and modding of Android apps and games.\033[0m"
    if platform.system() == "Linux":
        link = "https://TDOhex.t.me"
        user_input = input("\n\n\033[1;33mEnter 1 to visit TDOhex, or any other key to terminate: \033[0m")
        if user_input == "1":
            subprocess.run(["xdg-open", link])
            print("\n\033[1;35mHappy reversing!\nThanks to visit!\033[0m")
        else:
            print(message)
    else:
        print(message)

def main():
    welcome()
    check_radare2_installed()
    check_r2pipe_installed()
    prompt_file_path()
    print_architecture()
    prompt_all_offset_types()
    set_values_to_offsets(file_path, offsets)
    prompt_open_link()

if __name__ == "__main__":
    main()
