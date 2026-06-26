import backend.gridsim.visualization as v
import inspect

print("Loaded visualization.py from:", v.__file__)
print("Functions found:", [name for name, obj in inspect.getmembers(v) if inspect.isfunction(obj)])
