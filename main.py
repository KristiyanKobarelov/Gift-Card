from Functions.add import add_gift_card
from setup import sheet
from setup import spreadsheet
from Functions.remove import remove_gift_card, gift_card_used
from Functions.code_generator import create_code
from Functions.use_portion import use_portion
from Functions.print_info import print_info


def main():
    print("[DEBUG] Available tabs:", [ws.title for ws in spreadsheet.worksheets()])
    firstname = input("Enter first name: ")
    lastname = input("Enter last name: ")
    amount = int(input("Enter amount: "))

    while 1:
        choice = input("Choose an action - (A)dd, (R)emove, Mark as (U)sed, Use (P)ortion of the money, Pr(I)nt information, (Q)uit: ").upper()
        if choice == 'A':
            code = create_code(sheet, firstname, lastname)
            add_gift_card(sheet, code, amount, f"{firstname} {lastname}")
        elif choice == 'R':
            code = input("Enter gift card code to remove: ").strip()
            remove_gift_card(sheet, code)
        elif choice == 'U':
            code = input("Enter gift card code to mark as used: ").strip()
            gift_card_used(sheet, code)
        elif choice == 'P':
            code = input("Enter gift card code to use portion from: ").strip()
            portion_amount = int(input("Enter amount to use: "))
            use_portion(sheet, code, portion_amount)
        elif choice == 'I':
            code = input("Enter gift card code to print information: ").strip()
            print_info(sheet, code)
        elif choice == 'Q':
            print("Exiting the program.")
            break

if __name__ == "__main__":
    main()
