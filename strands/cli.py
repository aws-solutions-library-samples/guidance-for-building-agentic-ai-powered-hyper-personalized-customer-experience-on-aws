#!/usr/bin/env python3
from agents.hyperpersonal_search import create_hyperpersonal_search_agent

def main():
    print("\nHyperpersonal Health Assistant 🩺\n")
    print("Type 'quit' to exit")
    print("-" * 75)
    
    agent = create_hyperpersonal_search_agent()
    
    while True:
        try:
            user_input = input("\n:> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            if not user_input:
                continue

            response = agent(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
