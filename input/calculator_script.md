# Calculator Tutorial

## Step 1
narration: "Welcome to this Python calculator tutorial. Today we'll build a fully functional calculator from scratch. We'll cover addition, subtraction, multiplication, division, and even handle errors like dividing by zero. Let's start by creating a new Python file called calculator dot py."
code: |
  # calculator.py
  # A simple calculator in Python

## Step 2
narration: "First, let's implement the addition function. It takes two numbers as parameters and returns their sum. This is the simplest operation, but we'll follow the same pattern for all our functions."
code: |
  def add(a, b):
      """Return the sum of a and b."""
      return a + b

## Step 3
narration: "Next, subtraction. The subtract function takes two parameters: a and b, and returns a minus b. Notice how we're documenting every function with a docstring — this is good Python practice."
code: |
  def subtract(a, b):
      """Return the difference of a and b."""
      return a - b

## Step 4
narration: "Now let's add multiplication. The multiply function returns the product of a and b. Python uses the asterisk symbol for multiplication. Again, we keep it clean and simple."
code: |
  def multiply(a, b):
      """Return the product of a and b."""
      return a * b

## Step 5
narration: "Division needs special care. If someone tries to divide by zero, Python will raise a ZeroDivisionError. We handle that with a try-except block and return None to signal that the operation failed."
code: |
  def divide(a, b):
      """Return the quotient of a and b. Returns None if b is zero."""
      try:
          return a / b
      except ZeroDivisionError:
          print("Error: Cannot divide by zero.")
          return None

## Step 6
narration: "Now let's bring everything together with a calculate function. It takes an operator string and two numbers, then calls the right function based on the operator. If the operator isn't recognised, we return None and print a helpful message."
code: |
  def calculate(operator, a, b):
      """Dispatch to the correct operation based on operator string."""
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
narration: "Let's test each function to make sure they work correctly. We'll call each one and print the result. Run this file and you should see the correct output for all four operations."
code: |
  if __name__ == "__main__":
      print(add(10, 5))        # 15
      print(subtract(10, 5))   # 5
      print(multiply(10, 5))   # 50
      print(divide(10, 5))     # 2.0
      print(divide(10, 0))     # Error + None

## Step 8
narration: "Now let's build an interactive loop so a user can type in their own calculations. We use a while True loop that keeps running until the user types quit. We also use a try-except to handle invalid number inputs gracefully."
code: |
  def run_calculator():
      """Run an interactive calculator session."""
      print("Python Calculator — type 'quit' to exit")
      while True:
          user_input = input("\nEnter calculation (e.g. 10 + 5): ").strip()
          if user_input.lower() == "quit":
              print("Goodbye!")
              break
          parts = user_input.split()
          if len(parts) != 3:
              print("Format: <number> <operator> <number>")
              continue
          try:
              a = float(parts[0])
              operator = parts[1]
              b = float(parts[2])
          except ValueError:
              print("Invalid numbers. Please try again.")
              continue
          result = calculate(operator, a, b)
          if result is not None:
              print(f"Result: {result}")

## Step 9
narration: "Let's wire up the entry point. We call run underscore calculator only when the script is run directly, not when it's imported. This is the standard Python idiom using the name equals main guard."
code: |
  if __name__ == "__main__":
      run_calculator()

## Step 10
narration: "And that's our complete Python calculator! We covered four arithmetic operations, zero division handling, invalid input handling, and an interactive user loop. The full source is clean, well-documented, and easy to extend. Try adding a power operator or a modulo operator as a next step. Thanks for watching!"
code: |
  # Full calculator.py summary:
  # add, subtract, multiply, divide  — core operations
  # calculate(operator, a, b)        — dispatcher
  # run_calculator()                 — interactive loop
  # All functions are independently testable.