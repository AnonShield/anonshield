# src/anon/tqdm_handler.py
import logging
import os
from tqdm import tqdm


class HostPathFormatter(logging.Formatter):
    """Names the user's folders instead of the container mounts.

    The Docker wrappers mount the input at /anon_input and the output at
    /anon_output, and pass the host folders in ANON_HOST_INPUT_DIR and
    ANON_HOST_OUTPUT_DIR.
    """
    def format(self, record):
        message = super().format(record)
        for mount, variable in (("/anon_input", "ANON_HOST_INPUT_DIR"), ("/anon_output", "ANON_HOST_OUTPUT_DIR")):
            if os.environ.get(variable):
                message = message.replace(mount, os.environ[variable])
        return message

class TqdmLoggingHandler(logging.Handler):
    """
    A logging handler that redirects logging output to `tqdm.write()`.
    
    This prevents `tqdm` progress bars from being broken by log messages
    printed to the console.
    """
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        """Format and emit a log record via tqdm.write.

        Args:
            record: The log record to emit.
        """
        try:
            msg = self.format(record)
            tqdm.write(msg, file=None, end='\n')
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
