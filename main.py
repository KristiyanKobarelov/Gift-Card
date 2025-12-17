from Functions.add import add_gift_card
from setup import sheet
from Functions.remove import remove_gift_card, gift_card_used
from Functions.code_generator import create_code

def main():
    firstname = input("Enter first name: ")
    lastname = input("Enter last name: ")
    amount = int(input("Enter amount: "))
    description = input("Enter description: ")

    while 1:
        choice = input("Choose an action - (A)dd, (R)emove, Mark as (U)sed, (Q)uit: ").upper()
        if choice == 'A':
            code = create_code(sheet, firstname, lastname)
            add_gift_card(sheet, code, amount, f"{firstname} {lastname}", description)
        elif choice == 'R':
            code = input("Enter gift card code to remove: ").strip()
            remove_gift_card(sheet, code)
        elif choice == 'U':
            code = input("Enter gift card code to mark as used: ").strip()
            gift_card_used(sheet, code)
        elif choice == 'Q':
            print("Exiting the program.")
            break

if __name__ == "__main__":
    main()
