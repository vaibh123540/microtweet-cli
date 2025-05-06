# microtweet‑cli

A simple command‑line “micro‑tweet” client backed by a SQLite database.  
Allows users to sign up, log in, follow other users, post tweets, reply, retweet, search, and manage favorite lists—all from your terminal.

---

## Features

- **User authentication**  
  - Sign up with name, email, phone, password  
  - Log in / log out  

- **Home feed**  
  - View tweets & retweets from users you follow, newest first  

- **Search tweets**  
  - Keyword or hashtag search  
  - View tweet details (retweet & reply counts)  
  - Reply, retweet, or add to a favorite list  

- **Search users**  
  - Find users by name substring  
  - View user stats (tweet count, followers, following, recent tweets)  
  - Follow other users  

- **Compose tweets**  
  - Write new tweets with hashtag extraction  

- **Followers & lists**  
  - List your followers and followees  
  - Create and view “favorite lists” of tweets  

---

## Requirements

- Python 3.7+  
- SQLite3 (bundled with Python)  

---

## Setup

1. **Clone or download** this repository.  
2. **Create a SQLite database** and initialize the required tables. For example:

   ```sql
   -- users table
   CREATE TABLE users(
     usr      TEXT PRIMARY KEY,
     name     TEXT,
     email    TEXT,
     phone    TEXT,
     pwd      TEXT
   );

   -- tweets table
   CREATE TABLE tweets(
     tid         INTEGER PRIMARY KEY,
     writer_id   TEXT,
     text        TEXT,
     tdate       TEXT,
     ttime       TEXT,
     replyto_tid INTEGER,
     FOREIGN KEY(writer_id) REFERENCES users(usr),
     FOREIGN KEY(replyto_tid) REFERENCES tweets(tid)
   );

   -- retweets table
   CREATE TABLE retweets(
     tid           INTEGER,
     retweeter_id  TEXT,
     writer_id     TEXT,
     spam          INTEGER,
     rdate         TEXT,
     FOREIGN KEY(tid) REFERENCES tweets(tid),
     FOREIGN KEY(retweeter_id) REFERENCES users(usr)
   );

   -- follows table
   CREATE TABLE follows(
     flwer     TEXT,
     flwee     TEXT,
     start_date TEXT,
     FOREIGN KEY(flwer) REFERENCES users(usr),
     FOREIGN KEY(flwee) REFERENCES users(usr)
   );

   -- hashtag_mentions table
   CREATE TABLE hashtag_mentions(
     tid  INTEGER,
     term TEXT,
     FOREIGN KEY(tid) REFERENCES tweets(tid)
   );

   -- lists & include tables (for favorites)
   CREATE TABLE lists(
     owner_id TEXT,
     lname    TEXT,
     FOREIGN KEY(owner_id) REFERENCES users(usr)
   );
   CREATE TABLE include(
     owner_id TEXT,
     lname    TEXT,
     tid       INTEGER,
     FOREIGN KEY(owner_id, lname) REFERENCES lists(owner_id, lname),
     FOREIGN KEY(tid) REFERENCES tweets(tid)
   );

## Usage
```python3 twitter.py path/to/microtweet.db```