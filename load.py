import streamlit as st
import requests
import re
from groq import Groq

# Set your Groq API key
API_KEY = st.secrets["API_KEY"]

# Function to fetch tossups
def get_tossups(answerline, min_diff, max_diff):
    url = "https://qbreader.org/api/query"
    params = {
        "queryString": answerline,
        "questionType": "tossup",
        "searchType": "answer",
        "exactPhrase": True,
        "maxReturnLength": 1000,
        "difficulties": list(range(min_diff, max_diff + 1)),
        "minYear": 2010,
        "maxYear": 2025
    }
    r = requests.get(url, params=params)
    data = r.json()
    tossups = data["tossups"]["questionArray"]

    pattern = r'^\s*' + re.escape(answerline) + r'\s*(?:\[.*\])?$'
    filtered = [t for t in tossups if re.match(pattern, t["answer_sanitized"], re.IGNORECASE)]
    return filtered

# Streamlit UI
st.title("Quiz Bowl Question Generator")
st.write("Generate a new quiz bowl tossup based on real question data from QBReader.")

answerline = st.text_input("Enter the answerline:", "")
difficulty_range = st.slider("Select difficulty range:", 1, 10, (6, 10))

if st.button("Generate Question"):
    if not answerline.strip():
        st.warning("Please enter an answerline.")
    else:
        st.info("Fetching questions and generating new tossup...")

        # Fetch questions
        iron = get_tossups(answerline, difficulty_range[0], difficulty_range[1])

        client = Groq(api_key=API_KEY)

        # Collect questions
        questions = ""
        for x in iron:
            questions += x["question_sanitized"] + "\n"
            if len(questions) > 10000:
                break

        # Step 1: Extract common clues
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Given the following list of quiz bowl questions about " + answerline +
                               ", give me the " + str(max(len(iron)//3, 15)) +
                               " most common clues you see. Have the most common/easiest clues at the start of the list, "
                               "and the less common clues at the bottom. Give your response only as a sentence per clue in the exact format as in the question.\n"
                               + questions,
                }
            ],
            model="compound-beta",
        )

        # Step 2: Generate new question
        chat2 = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Here is a list of clues common in quiz bowl questions about " + answerline +
                               " (the most common clues are at the top, and the less common clues are at the bottom): " +
                               chat_completion.choices[0].message.content +
                               "\nUsing this, write a new quiz bowl question incorporating these clues and any outside knowledge to fill gaps. "
                               "The beginning of the question should have less common clues, and the end of the question should have more common clues. "
                               "Make the first sentence or two novel clues based on your knowledge of the subject if you see an opportunity for that. These should be harder and more obscure "
                               "than whatever is in the question and NOT INCLUDE THE ANSWERLINE AT ALL ANYWHERE IN THE CLUE. Add a powermark, denoted (*), where "
                               "the difficulty changes from harder to easier. It should be of the rough length and format: "
                               "This element is found in a catalyst used alongside hydrogen peroxide and acetic acid to oxidize aliphatic C-H bonds; that is the White-Chen catalyst. "
                               "This element is used as the catalyst in the high-temperature version of the Fischer-Tropsch process. "
                               "It’s not aluminum, but this element’s chloride can be used as a catalyst to electrophilically halogenate aromatic rings in the Friedel-Crafts reactions. "
                               "This metal is bound to two (*) cyclopentadienyl rings in the earliest discovered sandwich compound. "
                               "Aconitase and a class of compounds named for John Rieske contain clusters of this metal bound to sulfur. "
                               "A catalyst of this metal is used to produce ammonia in the Haber-Bosch process. "
                               "For 10 points, name this metal found alongside carbon in steel. Give only the question. Nothing else.",
                }
            ],
            model="compound-beta",
        )

        st.success("Here’s your generated question:")
        st.write(chat2.choices[0].message.content)
