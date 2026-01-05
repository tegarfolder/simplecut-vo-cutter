import time

TO_PIPE = r"\\.\pipe\ToSrvPipe"
FROM_PIPE = r"\\.\pipe\FromSrvPipe"


class AudacityPipeError(Exception):
    pass


def send(cmd):
    try:
        with open(TO_PIPE, "w") as f:
            f.write(cmd + "\n")

        with open(FROM_PIPE, "r") as f:
            return f.readline()
    except FileNotFoundError:
        raise AudacityPipeError("Audacity is not running or Script-Pipe not enabled")


def import_audio_and_label(audio_path):
    # Import audio (fully automatic)
    send(f'Import2: Filename="{audio_path}"')

    # Tunggu Audacity load audio
    time.sleep(1.0)

    # Import label (semi-manual: dialog akan muncul)
    send("ImportLabels:")