import sqlite3

# cards = {
#     'FRODO':{
#         'strength':4,
#         'stealth':10,
#         'shooting':4,
#         'magic':2,
#     },
#     'ARAGORN':{
#         'strength':8,
#         'stealth':8,
#         'shooting':7,
#         'magic':2,
#     },
#     'GIMLI':{
#         'strength':8,
#         'stealth':4,
#         'shooting':5,
#         'magic':0,
#     },
#     'LEGOLAS':{
#         'strength':7,
#         'stealth':10,
#         'shooting':10,
#         'magic':5,
#     }
# }

# values for strength, stealth, shooting, magic
# list below is order of attributes according to schema.sql
cards = {
    'FRODO':[4,10,4,2],
    'ARAGORN':[8,8,7,2],
    'GIMLI':[8,4,5,0],
    'LEGOLAS':[7,10,10,5],
    'GANDALF':[8,4,4,10],
    'SARUMAN':[7,4,2,9],
    'SAURON':[9,2,5,10],
    'GALADRIEL':[8,7,7,9],
    'GOLLUM':[2,9,2,0],
    'ARWEN':[7,9,7,6]
}

connection = sqlite3.connect('top-trumps-db.db')

with open('schema.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()

cur.execute("INSERT OR REPLACE INTO users (username, password) VALUES (?,?)",
            ("computer", "22d408a88a989b8b24d2082b1a8f8eab3d248cec"))

attributes = cur.execute("PRAGMA table_info(cards)").fetchall()
# drop first 2 elements which are id and title, as defined in schema.sql
attrib_list = [x[1] for x in attributes[2:]]
joined_attrib_list = ', '.join(attrib_list)
print(joined_attrib_list)

for card in cards:
    print(card)
    cur.execute("INSERT INTO cards (title," + joined_attrib_list + ") VALUES (?"+",?"*(len(attrib_list))+")",
                tuple([card] + cards[card]))

connection.commit()
connection.close()