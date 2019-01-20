#%%
from tqdm import tqdm_notebook
msg = "Hello World"
print(msg)
pbar = tqdm_notebook(total=100)
pbar.update(50)