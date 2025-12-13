# src/anon/tqdm_handler.py
import logging
from tqdm import tqdm

class TqdmLoggingHandler(logging.Handler):
    """
    A logging handler that redirects logging output to `tqdm.write()`.
    
    This prevents `tqdm` progress bars from being broken by log messages
    printed to the console.
    """
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg, file=None, end='\n')
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
