"""Terminal chat loop: read input, ask the model, print the reply."""

from llm import ask_model

# Temporary prompt for step 2. From step 4 on, the agent uses prompts/system.md.
SYSTEM_PROMPT = "You are a friendly assistant. Keep answers short."


def main() -> None:
    """Chat with the model until the user types exit."""
    print("Notes Assistant (step 2: chat only). Type 'exit' to quit.")
    while True:
        try:
            user_message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break  # Ctrl+C or Ctrl+Z quits cleanly instead of showing a traceback
        if user_message.lower() == "exit":
            break
        if not user_message:
            continue

        try:
            # Only the latest message is sent, so the model forgets earlier turns.
            reply = ask_model(SYSTEM_PROMPT, f"USER: {user_message}")
        except RuntimeError as error:
            # One failed call shouldn't end the whole chat.
            reply = f"(error) {error}"
        print(f"Assistant: {reply}")
    print("Bye!")


if __name__ == "__main__":
    main()
