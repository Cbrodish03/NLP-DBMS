import spacy
from spacy import matcher

# NOTE: do the following before running
# pip install spacy
# python -m spacy download en_core_web_sm

# if running python interpreter on 3.12.4, do
# pip install pydantic==2.7.4

# example found at https://course.spacy.io/en/chapter1

# create a blank English nlp object
nlp = spacy.blank("en")

# process string of text
doc = nlp("Hello World!")

# iterate over tokens
for token in doc:
    print(token.text)

# index second token
print(doc[1].text)

# slice from doc
print(doc[1:3].text)

# lexical attributes
print("Index:   ", [token.i for token in doc])
print("Text:    ", [token.text for token in doc])
print("is_alpha:", [token.is_alpha for token in doc])
print("is_punct:", [token.is_punct for token in doc])
print("like_num:", [token.like_num for token in doc])

# load small english pipeline
# nlp = en_core_web_sm.load()
nlp = spacy.load('en_core_web_sm')
doc = nlp("She ate the pizza")

for token in doc:
    # print text and predicted part-of-speech tag
    print(token.text, token.pos_)

for token in doc:
    print(token.text, token.pos_, token.dep_, token.head.text)


# Process a text
doc = nlp("Apple is looking at buying U.K. startup for $1 billion")

# Iterate over the predicted entities
for ent in doc.ents:
    # Print the entity text and its label
    print(ent.text, ent.label_)

# ------------------------
text = "It’s official: Apple is the first U.S. public company to reach a $1 trillion market value"

# Process the text
doc = nlp(text)

for token in doc:
    # Get the token text, part-of-speech tag and dependency label
    token_text = token.text
    token_pos = token.pos_
    token_dep = token.dep_
    # This is for formatting only
    print(f"{token_text:<12}{token_pos:<10}{token_dep:<10}")

# Iterate over the predicted entities
for ent in doc.ents:
    # Print the entity text and its label
    print(ent.text, ent.label_)

# -------------------------
# USING THE MATCHER

