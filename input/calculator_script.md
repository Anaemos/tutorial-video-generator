# Calculator Tutorial

## Explainer
pause_ms: 1800, 1800
narration: "Before we dive into writing the Python code for our simple calculator, let's take a moment to understand the core concepts that make it work. We will be using functions, passing inputs as parameters, returning results, and applying mathematical operators. These components are the fundamental building blocks of our program. Let's trace how they connect in a logical flow: we take inputs, pass them into our function, apply the operator, and finally receive the computed output result."
nodes:
  - id: n1, label: "Inputs (a, b)", kind: input
  - id: n2, label: "Function", kind: process
  - id: n3, label: "Operator", kind: process
  - id: n4, label: "Result", kind: output
edges:
  - from: n1, to: n2, label: "passed as"
  - from: n2, to: n3, label: "applies"
  - from: n3, to: n4, label: "returns"

## Explainer
pause_ms: 1500, 1500
narration: "Now let's look at the error path. Division is the one operation where we need a safety check, because zero in the denominator can crash the program. The calculator first tries the division, then catches the error if it happens, and finally prints a friendly message instead of breaking. That extra branch is what makes the app feel polished and reliable."
nodes:
  - id: n1, label: "Inputs", kind: input
  - id: n2, label: "divide(a, b)", kind: process
  - id: n3, label: "Zero?", kind: decision
  - id: n4, label: "Result", kind: output
  - id: n5, label: "Error msg", kind: note
edges:
  - from: n1, to: n2, label: "call"
  - from: n2, to: n3, label: "check"
  - from: n3, to: n4, label: "no"
  - from: n3, to: n5, label: "yes"

## Step 1
narration: "Welcome to this Python calculator tutorial. Today we are going to build a fully functional calculator program from scratch using Python. By the end of this video, you will have a complete calculator that supports addition, subtraction, multiplication, and division. We will also handle edge cases like dividing by zero, and we will build an interactive loop so users can type in their own calculations. Let's get started by creating a new Python file called calculator dot py and adding a comment at the top to describe what it does."
code: |
  # calculator.py
  # A simple yet complete calculator built in Python.
  # Supports: addition, subtraction, multiplication, division.
  # Includes error handling for division by zero and invalid input.

## Step 2
narration: "Let's implement the addition function first. This function takes two parameters, a and b, and returns their sum using the plus operator. We also add a docstring which is a string right below the function definition that describes what the function does. Docstrings are important for documentation and they show up in editor tooltips when other developers use your function. Even for a simple function like this, it is good practice to include one."
code: |
  def add(a, b):
      """Return the sum of a and b."""
      return a + b

## Step 3
narration: "Next up is the subtraction function. It follows the exact same pattern as addition — two parameters, a docstring, and a single return statement. The only difference is the operator. Notice how consistent the structure is across all our functions. This consistency makes the code easy to read and easy to extend later. If you wanted to add a modulo or power function, you would follow this exact same pattern."
code: |
  def subtract(a, b):
      """Return the result of a minus b."""
      return a - b

## Step 4
narration: "Now let's add the multiplication function. In Python, multiplication uses the asterisk symbol, not the letter x. So a times b is written as a asterisk b. Again we follow the same structure: function name, two parameters, docstring, and return statement. Keeping all four arithmetic functions consistent like this is important because it allows us to call them all the same way in our dispatcher function that we will write in a moment."
code: |
  def multiply(a, b):
      """Return the product of a and b."""
      return a * b

## Step 5
narration: "Division requires more care than the other three operations. If someone passes zero as the second argument, Python will raise a ZeroDivisionError and crash the program. To handle this gracefully, we wrap the division inside a try except block. If the division succeeds, we return the result. If a ZeroDivisionError is raised, we catch it, print a helpful error message, and return None to signal to the caller that the operation could not be completed. This is a much better experience than letting the program crash."
code: |
  def divide(a, b):
      """Return the quotient of a divided by b. Returns None if b is zero."""
      try:
          return a / b
      except ZeroDivisionError:
          print("Error: Cannot divide by zero.")
          return None

## Step 6
narration: "Now let's write the calculate function which acts as a dispatcher. It takes three arguments: an operator string like plus, minus, asterisk, or slash, and two numbers a and b. Based on the operator, it calls the correct function. We use a chain of if and elif statements to check which operator was passed. If none of them match, we print an error message and return None. This dispatcher pattern means the rest of our program only needs to call calculate — it never needs to know which specific function to call directly."
code: |
  def calculate(operator, a, b):
      """Call the correct arithmetic function based on the operator string."""
      if operator == "+":
          return add(a, b)
      elif operator == "-":
          return subtract(a, b)
      elif operator == "*":
          return multiply(a, b)
      elif operator == "/":
          return divide(a, b)
      else:
          print(f"Error: Unknown operator '{operator}'.")
          return None

## Step 7
narration: "Before we build the interactive loop, let's write a quick test block to verify all four operations work correctly. We call each function directly and print the results. Add ten plus five should give fifteen. Subtract ten minus five should give five. Multiply ten times five should give fifty. Divide ten by five should give two point zero. And dividing ten by zero should print our error message and return None. Run the file now and confirm all five outputs are correct."
code: |
  # Quick tests — verify all operations work before building the interactive loop
  print("Testing calculator functions:")
  print(f"  add(10, 5)      = {add(10, 5)}")        # 15
  print(f"  subtract(10, 5) = {subtract(10, 5)}")   # 5
  print(f"  multiply(10, 5) = {multiply(10, 5)}")   # 50
  print(f"  divide(10, 5)   = {divide(10, 5)}")      # 2.0
  print(f"  divide(10, 0)   = {divide(10, 0)}")      # Error + None

## Step 8
narration: "Now let's build the interactive calculator loop. The run calculator function uses a while True loop that keeps running indefinitely until the user types quit. Inside the loop, we read a line of input from the user and split it into three parts: a number, an operator, and another number. If the input doesn't have exactly three parts, we print a format hint and continue to the next iteration. We also wrap the number parsing in a try except block to handle cases where the user types something that isn't a valid number. If everything is valid, we call our calculate function and print the result."
code: |
  def run_calculator():
      """Run an interactive calculator session in the terminal."""
      print("Python Calculator — type 'quit' to exit.")
      while True:
          user_input = input("\nEnter calculation (e.g. 10 + 5): ").strip()
          if user_input.lower() == "quit":
              print("Goodbye!")
              break
          parts = user_input.split()
          if len(parts) != 3:
              print("Please use the format: <number> <operator> <number>")
              continue
          try:
              a = float(parts[0])
              operator = parts[1]
              b = float(parts[2])
          except ValueError:
              print("Invalid numbers entered. Please try again.")
              continue
          result = calculate(operator, a, b)
          if result is not None:
              print(f"Result: {result}")

## Step 9
narration: "Let's wire up the entry point. We add a main guard at the bottom of the file that calls run calculator. The if name equals main pattern ensures that run calculator is only called when you run the file directly from the terminal. If another Python file were to import our calculator module, this block would be skipped — which means the interactive loop would not start unexpectedly. This is standard Python practice and you should use it in every script you write."
code: |
  if __name__ == "__main__":
      run_calculator()

## Step 10
narration: "And that is our complete Python calculator. We have a clean, well-documented program with four arithmetic operations, proper error handling for division by zero and invalid input, and a friendly interactive loop. Try running it now: type python calculator dot py in your terminal, then test it with something like ten plus five, twenty divided by four, and ten divided by zero to see the friendly error message instead of a crash. When you are done, type quit to exit cleanly. That is a fully functional, well-structured Python calculator built from scratch. Thanks for watching, and try extending it with a power operator or a square root function as a next step!"
code: |
  # calculator.py is now complete.
  # Run it with: python calculator.py
  # Try: 10 + 5, 20 / 4, 10 / 0, quit
