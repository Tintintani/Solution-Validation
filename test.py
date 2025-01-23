RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'  

x = [1, 2, 3, 4, 5]
print(RED + 'This is red')
print(', '.join(map(str, x)) + RESET)
