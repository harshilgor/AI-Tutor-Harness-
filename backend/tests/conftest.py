"""Keep the regular test suite offline and free of provider charges."""

import os


os.environ["AI_TUTOR_PROVIDER"] = "deterministic_baseline"
