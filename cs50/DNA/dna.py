import csv
import sys


def main():
    # TODO: Check for command-line usage
    if len(sys.argv) != 3:
        sys.exit("Usage: python dna.py data.csv sequence.txt")

    # TODO: Read database file into a variable
    with open(sys.argv[1], "r") as f:
        reader = csv.DictReader(f)
        data = list()
        for row in reader:
            data.append(row)
            keys = list(row.keys())
            # print(key)

        # TODO: Read DNA sequence file into a variable
        with open(sys.argv[2], "r") as f:
            seq = csv.reader(f)

            # TODO: Find longest match of each STR in DNA sequence
            m = 0
            all_repeat = dict()
            for item in seq:
                for key in keys:
                    # print(key)
                    m = max(m, int(longest_match(item[0], key)))
                    all_repeat[key] = m
                    m = 0

            # TODO: Check database for matching profiles
            # data.pop(0)
            # print(data)

            for person in data:
                you = True
                for key in keys:
                    if key == "name":
                        continue
                    # print(f"{int(person[key])} == {int(all_repeat[key])}")
                    if int(person[key]) != int(all_repeat[key]):
                        you = False
                    # print(you)
                if you:
                    print(person["name"])
                    return

        print("No match")

    return


def longest_match(sequence, subsequence):
    """Returns length of longest run of subsequence in sequence."""

    # Initialize variables
    longest_run = 0
    subsequence_length = len(subsequence)
    sequence_length = len(sequence)

    # Check each character in sequence for most consecutive runs of subsequence
    for i in range(sequence_length):
        # Initialize count of consecutive runs
        count = 0

        # Check for a subsequence match in a "substring" (a subset of characters) within sequence
        # If a match, move substring to next potential match in sequence
        # Continue moving substring and checking for matches until out of consecutive matches
        while True:
            # Adjust substring start and end
            start = i + count * subsequence_length
            end = start + subsequence_length

            # If there is a match in the substring
            if sequence[start:end] == subsequence:
                count += 1

            # If there is no match in the substring
            else:
                break

        # Update most consecutive matches found
        longest_run = max(longest_run, count)

    # After checking for runs at each character in seqeuence, return longest run found
    return longest_run


main()
