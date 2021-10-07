"""
This program and the accompanying materials are made available under the terms of the
Eclipse Public License v2.0 which accompanies this distribution, and is available at
https://www.eclipse.org/legal/epl-v20.html
SPDX-License-Identifier: EPL-2.0

Copyright Contributors to the Zincware Project.

Description: Type hinting class for IDE autocompletion
"""
from pytrack.core.py_track import PyTrackParent
from pytrack.core.parameter import DVC


class TypeHintParent:
    def __init__(self):
        self.pytrack: PyTrackParent = PyTrackParent(child=self)
        self._executed = DVC.result()
