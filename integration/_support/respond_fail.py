
if input("What's the password?") == "Rosebud":
    print("You're not Citizen Kane!")
    # This should sit around forever like e.g. a bad sudo prompt would, but the
    # responder ought to be looking for the above and aborting instead.
    input("Seriously, what's the password???")
