import sqlite3
import sys
import getpass
import re
import datetime

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 twitter.py <database_file>")
        sys.exit(1)

    db_name = sys.argv[1]
    conn = sqlite3.connect(db_name)
    conn.execute("PRAGMA foreign_keys = ON;")

    current_user_id = None

    while True:
        if current_user_id is None:
            choice = login_menu()
            if choice == '1':
                user_id = login(conn)
                if user_id is not None:
                    current_user_id = user_id
                    show_followed_tweets(conn, current_user_id)
                else:
                    print("Login failed.")
            elif choice == '2':
                user_id = signup(conn)
                if user_id is not None:
                    current_user_id = user_id
                    show_followed_tweets(conn, current_user_id)
            elif choice == '3':
                print("Exiting. Goodbye!")
                break
            else:
                print("Invalid choice. Try again.")
        else:
            choice = main_menu()
            if choice == '1':
                search_tweets(conn, current_user_id)
            elif choice == '2':
                search_users(conn, current_user_id)
            elif choice == '3':
                compose_tweet(conn, current_user_id)
            elif choice == '4':
                list_followers(conn, current_user_id)
            elif choice == '5':
                list_favorite_lists(conn, current_user_id)
            elif choice == '6':
                current_user_id = None
            else:
                print("Invalid choice. Try again.")

    conn.close()


def login_menu():
    print("\n--- Login Menu ---")
    print("1. Login")
    print("2. Sign up")
    print("3. Exit")
    return input("Enter your choice: ").strip()

def main_menu():
    print("\n--- Main Menu ---")
    print("1. Search Tweets")
    print("2. Search Users")
    print("3. Compose a Tweet")
    print("4. List Followers")
    print("5. List Favorite Lists")
    print("6. Logout")
    return input("Enter your choice: ").strip()


def login(conn):
    print("\n--- Login ---")
    usr = input("User ID: ").strip()

    pwd = getpass.getpass("Password: ")

    cur = conn.cursor()
    query = "SELECT usr FROM users WHERE usr = ? AND pwd = ?"
    cur.execute(query, (usr, pwd))
    row = cur.fetchone()
    if row:
        print("Login successful.")
        return row[0]
    else:
        return None


def signup(conn):
    """
    Unregistered user can sign up by providing name, email, phone, pwd.
    The system generates the user ID (1 + max(usr)).
    """
    print("\n--- Signup ---")
    name = input("Enter name: ").strip()
    email = input("Enter email: ").strip()
    phone = input("Enter phone: ").strip()
    pwd = getpass.getpass("Enter password: ")

    if "@" not in email or "." not in email:
        print("Invalid email format.")
        return None
    
    cur = conn.cursor()
    cur.execute("SELECT MAX(usr) FROM users")
    result = cur.fetchone()
    max_id = result[0] if result and result[0] is not None else 0
    new_id = int(max_id) + 1

    insert_query = """
        INSERT INTO users(usr, name, email, phone, pwd)
        VALUES (?, ?, ?, ?, ?)
    """
    try:
        cur.execute(insert_query, (new_id, name, email, phone, pwd))
        conn.commit()
        print(f"Signup successful! Your user ID is {new_id}")
        return str(new_id)
    except Exception as e:
        print(f"Error signing up: {e}")
        conn.rollback()
        return None


def show_followed_tweets(conn, current_user_id):
    """
    List all tweets and retweets (spam=0) from users who are being followed by current_user_id,
    ordered by date desc. Show 5 at a time with an option to show more.
    This retrieves tweet/retweet info from 'tweets' and 'retweets'.
    """
    print("\n--- Your Feed (Followed Users' Tweets/Retweets) ---")

    cur = conn.cursor()

    tweet_query = """
    SELECT
        'tweet' AS ttype,
        t.tid,
        t.tdate,
        t.ttime,
        0 AS spam
    FROM tweets t
    WHERE t.writer_id IN
        (SELECT flwee FROM follows WHERE flwer = ?)
    """

    retweet_query = """
    SELECT
        'retweet' AS ttype,
        r.tid,
        r.rdate AS tdate,
        NULL AS ttime,
        r.spam
    FROM retweets r
    WHERE r.retweeter_id IN
        (SELECT flwee FROM follows WHERE flwer = ?)
      AND r.spam = 0
    """

    union_query = f"""
    SELECT * FROM (
        {tweet_query}
        UNION
        {retweet_query}
    )
    ORDER BY tdate DESC
    """

    cur.execute(union_query, (current_user_id, current_user_id))
    results = cur.fetchall()

    index = 0
    while True:
        chunk = results[index:index+5]
        if not chunk:
            break
        for row in chunk:
            ttype, tid, date, ttime, spam = row
            print(f"{ttype.upper()} | tid={tid} | date={date} | time={ttime or 'N/A'} | spam={spam}")
        index += 5
        if index >= len(results):
            break
        choice = input("Show more? (y/n): ").strip().lower()
        if choice != 'y':
            break


def search_tweets(conn, current_user_id):
    """
    The user enters one or more keywords separated by commas.
    A tweet matches a keyword if:
      - keyword has prefix '#' and tweet's hashtag_mentions table has that term (case-insensitive), or
      - keyword does not have '#' and appears in tweet text (case-insensitive),
        or the tweet has that hashtag anyway.
    Show 5 at a time, user can select a tweet to see stats (#retweets, #replies),
    then optionally reply, retweet, or add to a favorite list.
    """
    print("\n--- Search Tweets ---")
    keywords_input = input("Enter keywords (comma-separated). Use # for hashtag search: ")
    keywords = [k.strip().lower() for k in keywords_input.split(',') if k.strip()]

    if not keywords:
        print("No keywords entered. Returning.")
        return

    cur = conn.cursor()

    matched_tids = set()

    for kw in keywords:
        if kw.startswith('#'):
            term = kw[1:]
            tag_query = """
                SELECT tid
                FROM hashtag_mentions
                WHERE lower(term) = ?
            """
            cur.execute(tag_query, (term,))
            rows = cur.fetchall()
            for r in rows:
                matched_tids.add(r[0])
        else:
            text_query = """
                SELECT tid
                FROM tweets
                WHERE lower(text) LIKE ?
            """
            cur.execute(text_query, (f"%{kw}%",))
            rows_text = cur.fetchall()
            for r in rows_text:
                matched_tids.add(r[0])

            tag_query = """
                SELECT tid
                FROM hashtag_mentions
                WHERE lower(term) = ?
            """
            cur.execute(tag_query, (kw,))
            rows_tag = cur.fetchall()
            for r in rows_tag:
                matched_tids.add(r[0])

    if not matched_tids:
        print("No tweets found for your keywords.")
        return

    tweet_details_query = f"""
        SELECT tid, writer_id, tdate, ttime, text
        FROM tweets
        WHERE tid IN ({','.join(['?']*len(matched_tids))})
        ORDER BY tdate DESC, ttime DESC
    """
    cur.execute(tweet_details_query, tuple(matched_tids))
    results = cur.fetchall()

    index = 0
    while True:
        chunk = results[index:index+5]
        if not chunk:
            break
        print("\n--- Search Results (page) ---")
        for i, row in enumerate(chunk):
            tid, writer_id, tdate, ttime, text = row
            print(f"{index + i + 1}. TID={tid}, WRITER={writer_id}, DATE={tdate}, TIME={ttime}, TEXT={text}")
        index += 5
        if index >= len(results):
            break
        choice = input("Show more? (y/n): ").strip().lower()
        if choice != 'y':
            break

    if results:
        selection = input("\nEnter the number of a tweet to view options (or blank to skip): ").strip()
        if selection.isdigit():
            selection_idx = int(selection) - 1
            if 0 <= selection_idx < len(results):
                tid, writer_id, tdate, ttime, text = results[selection_idx]
                tweet_options(conn, current_user_id, tid)
            else:
                print("Invalid tweet selection.")
        else:
            print("Skipped.")


def tweet_options(conn, current_user_id, tid):
    """
    Show stats: # retweets, # replies
    Then allow user to:
      - reply
      - retweet
      - add to a favorite list
    """
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM retweets WHERE tid=?", (tid,))
    num_retweets = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tweets WHERE replyto_tid=?", (tid,))
    num_replies = cur.fetchone()[0]

    print(f"\n--- Tweet TID={tid} Stats ---")
    print(f"Number of retweets: {num_retweets}")
    print(f"Number of replies: {num_replies}")

    while True:
        print("\nOptions:")
        print("1. Reply to Tweet")
        print("2. Retweet")
        print("3. Add to Favorite List")
        print("4. Back to Main Menu")
        opt = input("Choose an option: ").strip()
        if opt == '1':
            reply_to_tweet(conn, current_user_id, tid)
        elif opt == '2':
            retweet_tweet(conn, current_user_id, tid)
        elif opt == '3':
            add_to_favorite_list(conn, current_user_id, tid)
        elif opt == '4':
            break
        else:
            print("Invalid option.")


def reply_to_tweet(conn, current_user_id, replyto_tid):
    print("\n--- Reply to Tweet ---")
    text = input("Enter your reply text: ")

    cur = conn.cursor()
    cur.execute("SELECT MAX(tid) FROM tweets")
    row = cur.fetchone()
    max_tid = row[0] if row and row[0] is not None else 0
    new_tid = max_tid + 1

    now = datetime.datetime.now()
    tdate = now.strftime("%Y-%m-%d")
    ttime = now.strftime("%H:%M:%S")

    insert_query = """
        INSERT INTO tweets(tid, writer_id, text, tdate, ttime, replyto_tid)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        cur.execute(insert_query, (new_tid, current_user_id, text, tdate, ttime, replyto_tid))
        conn.commit()
        print(f"Reply posted (TID={new_tid}).")
    except Exception as e:
        conn.rollback()
        print(f"Error replying: {e}")


def retweet_tweet(conn, current_user_id, tid):
    print("\n--- Retweet ---")
    cur = conn.cursor()

    cur.execute("SELECT writer_id FROM tweets WHERE tid=?", (tid,))
    row = cur.fetchone()
    if not row:
        print("Tweet does not exist for retweet.")
        return
    writer_id = row[0]
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    insert_query = """
        INSERT INTO retweets(tid, retweeter_id, writer_id, spam, rdate)
        VALUES (?, ?, ?, ?, ?)
    """
    try:
        cur.execute(insert_query, (tid, current_user_id, writer_id, 0, now))
        conn.commit()
        print("Retweeted successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error retweeting: {e}")


def add_to_favorite_list(conn, current_user_id, tid):
    print("\n--- Add to Favorite List ---")
    cur = conn.cursor()
    cur.execute("SELECT lname FROM lists WHERE owner_id=?", (current_user_id,))
    lists = [row[0] for row in cur.fetchall()]
    if not lists:
        print("You have no favorite lists. Create one first (via manual SQL or extend code).")
        return

    print("Your favorite lists:")
    for i, lname in enumerate(lists):
        print(f"{i+1}. {lname}")
    choice = input("Select a list number (or blank to cancel): ").strip()
    if not choice.isdigit():
        print("Cancelled.")
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(lists):
        print("Invalid list selection.")
        return

    lname = lists[idx]
    insert_query = """
        INSERT INTO include(owner_id, lname, tid)
        VALUES (?, ?, ?)
    """
    try:
        cur.execute(insert_query, (current_user_id, lname, tid))
        conn.commit()
        print(f"Tweet {tid} added to list '{lname}'.")
    except Exception as e:
        conn.rollback()
        print(f"Error adding to favorite list: {e}")


def search_users(conn, current_user_id):
    """
    The user enters a single keyword. Show all users whose names contain that keyword
    (case-insensitive). Sort by ascending length of name. Show 5 at a time. Then can
    select a user to see details: (#tweets, #following, #followers, last 3 tweets).
    Then optionally follow that user or see more tweets.
    """
    print("\n--- Search Users ---")
    keyword = input("Enter a keyword to find in user names: ").strip().lower()
    if not keyword:
        return

    cur = conn.cursor()
    query = """
        SELECT usr, name
        FROM users
        WHERE lower(name) LIKE ?
    """
    cur.execute(query, (f"%{keyword}%",))
    rows = cur.fetchall()
    rows.sort(key=lambda x: len(x[1]))

    index = 0
    while True:
        chunk = rows[index:index+5]
        if not chunk:
            break
        for i, row in enumerate(chunk):
            uid, uname = row
            print(f"{index + i + 1}. UserID={uid}, Name={uname}")
        index += 5
        if index >= len(rows):
            break
        choice = input("Show more? (y/n): ").strip().lower()
        if choice != 'y':
            break

    if rows:
        selection = input("\nEnter the number of a user to see details (blank to skip): ").strip()
        if selection.isdigit():
            selection_idx = int(selection) - 1
            if 0 <= selection_idx < len(rows):
                user_id, uname = rows[selection_idx]
                show_user_details(conn, current_user_id, user_id)
            else:
                print("Invalid selection.")
        else:
            print("Skipped.")


def show_user_details(conn, current_user_id, user_id):
    """
    Show #tweets, #following, #followers, up to 3 most recent tweets.
    Then can follow that user or see more tweets.
    """
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tweets WHERE writer_id=?", (user_id,))
    num_tweets = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM follows WHERE flwer=?", (user_id,))
    num_following = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM follows WHERE flwee=?", (user_id,))
    num_followers = cur.fetchone()[0]

    print(f"\n--- User {user_id} Details ---")
    print(f"Total tweets: {num_tweets}")
    print(f"Follows: {num_following}")
    print(f"Followers: {num_followers}")

    cur.execute("""
        SELECT tid, text, tdate, ttime
        FROM tweets
        WHERE writer_id=?
        ORDER BY tdate DESC, ttime DESC
        LIMIT 3
    """, (user_id,))
    recents = cur.fetchall()
    if recents:
        print("Most recent tweets:")
        for r in recents:
            print(f"   TID={r[0]}, DATE={r[2]}, TIME={r[3]}, TEXT={r[1]}")
    else:
        print("No recent tweets.")

    while True:
        print("\nOptions:")
        print("1. Follow this user")
        print("2. See more tweets by this user")
        print("3. Back")
        choice = input("Choose an option: ").strip()
        if choice == '1':
            follow_user(conn, current_user_id, user_id)
        elif choice == '2':
            list_user_tweets(conn, user_id)
        elif choice == '3':
            break
        else:
            print("Invalid input.")


def follow_user(conn, current_user_id, user_to_follow):
    if current_user_id == user_to_follow:
        print("You cannot follow yourself.")
        return
    cur = conn.cursor()
    cur.execute("SELECT * FROM follows WHERE flwer=? AND flwee=?", (current_user_id, user_to_follow))
    if cur.fetchone():
        print("You already follow this user.")
        return
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        cur.execute("INSERT INTO follows(flwer, flwee, start_date) VALUES (?,?,?)",
                    (current_user_id, user_to_follow, now))
        conn.commit()
        print("Followed user successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error following user: {e}")


def list_user_tweets(conn, user_id):
    print(f"\n--- Tweets by User {user_id} ---")
    cur = conn.cursor()
    query = """
        SELECT tid, text, tdate, ttime
        FROM tweets
        WHERE writer_id=?
        ORDER BY tdate DESC, ttime DESC
    """
    cur.execute(query, (user_id,))
    results = cur.fetchall()
    index = 0
    while True:
        chunk = results[index:index+5]
        if not chunk:
            break
        for row in chunk:
            tid, text, tdate, ttime = row
            print(f"TID={tid}, DATE={tdate}, TIME={ttime}, TEXT={text}")
        index += 5
        if index >= len(results):
            break
        choice = input("Show more? (y/n): ").strip().lower()
        if choice != 'y':
            break


def compose_tweet(conn, current_user_id):
    """
    The user composes a tweet that may have hashtags (#something).
    We'll extract hashtags, store them in hashtag_mentions.
    Make sure not to insert duplicates for the same tweet.
    """
    print("\n--- Compose Tweet ---")
    text = input("Enter your tweet text: ")

    cur = conn.cursor()
    cur.execute("SELECT MAX(tid) FROM tweets")
    row = cur.fetchone()
    max_tid = row[0] if row and row[0] is not None else 0
    new_tid = max_tid + 1

    now = datetime.datetime.now()
    tdate = now.strftime("%Y-%m-%d")
    ttime = now.strftime("%H:%M:%S")

    insert_query = """
        INSERT INTO tweets(tid, writer_id, text, tdate, ttime, replyto_tid)
        VALUES (?, ?, ?, ?, ?, NULL)
    """
    try:
        cur.execute(insert_query, (new_tid, current_user_id, text, tdate, ttime))
        conn.commit()
        print(f"Tweet posted (TID={new_tid}).")
    except Exception as e:
        conn.rollback()
        print(f"Error posting tweet: {e}")
        return

    hashtags = set()
    for match in re.findall(r"#(\w+)", text, flags=re.IGNORECASE):
        hashtags.add(match.lower())

    for h in hashtags:
        try:
            cur.execute("INSERT INTO hashtag_mentions(tid, term) VALUES (?, ?)", (new_tid, h))
        except:
            pass
    conn.commit()
    if hashtags:
        print(f"Hashtags added: {', '.join(hashtags)}")


def list_followers(conn, current_user_id):
    """
    The user should be able to list all users who follow them (follows.flwee = current_user_id).
    Show 5 at a time.
    Then can select a follower -> show details (#tweets, #following, #followers, up to 3 tweets),
    option to follow them, or see more tweets, etc.
    """
    print("\n--- List Followers ---")
    cur = conn.cursor()
    query = """
        SELECT flwer
        FROM follows
        WHERE flwee=?
    """
    cur.execute(query, (current_user_id,))
    rows = cur.fetchall()
    followers = [r[0] for r in rows]
    if not followers:
        print("No one follows you.")
        return

    index = 0
    while True:
        chunk = followers[index:index+5]
        if not chunk:
            break
        for i, fid in enumerate(chunk):
            print(f"{index + i + 1}. UserID={fid}")
        index += 5
        if index >= len(followers):
            break
        choice = input("Show more? (y/n): ").strip().lower()
        if choice != 'y':
            break

    if followers:
        selection = input("\nEnter the number of a follower to see details (blank to skip): ").strip()
        if selection.isdigit():
            selection_idx = int(selection) - 1
            if 0 <= selection_idx < len(followers):
                follower_id = followers[selection_idx]
                show_user_details(conn, current_user_id, follower_id)
            else:
                print("Invalid selection.")
        else:
            print("Skipped.")


def list_favorite_lists(conn, current_user_id):
    """
    Show all of the user's favorite lists and the TIDs in them.
    """
    print("\n--- List Favorite Lists ---")
    cur = conn.cursor()
    lists_query = "SELECT lname FROM lists WHERE owner_id=?"
    cur.execute(lists_query, (current_user_id,))
    rows = cur.fetchall()
    if not rows:
        print("You have no favorite lists.")
        return

    for row in rows:
        lname = row[0]
        print(f"\nList: {lname}")
        inc_query = "SELECT tid FROM include WHERE owner_id=? AND lname=?"
        cur.execute(inc_query, (current_user_id, lname))
        inc_rows = cur.fetchall()
        if inc_rows:
            tids = [str(r[0]) for r in inc_rows]
            print("TIDs:", ", ".join(tids))
        else:
            print("No TIDs in this list.")


if __name__ == "__main__":
    main()