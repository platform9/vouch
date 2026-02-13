#!/usr/bin/env python3

from pecan import Pecan, expose
from root import RootController

app = Pecan(RootController())
