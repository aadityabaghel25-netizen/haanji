"""
Labelled caller utterances for the evaluation. (text, intent, order number or None).

TUNE was used while writing the rules in haanji/brain.py. HOLDOUT was written before the first evaluation run and is
frozen: never change the rules or these labels because of a held-out result. Both sets were written by us (the builders),
in the way customers type and speak Hinglish, so they are easier than real calls. Real-call accuracy will be lower.
"""

TUNE = [
    ("Mera kurti wala order kab tak aayega?", "status", None),
    ("Order four eight two one ka status kya hai?", "status", "4821"),
    ("Hello, mera parcel kahan pahuncha?", "status", None),
    ("Can you tell me where my order is?", "status", None),
    ("Mera bedsheet abhi tak nahi mila.", "not_received", None),
    ("Parcel deliver dikha raha hai par mujhe mila hi nahi.", "not_received", None),
    ("I never received my order, it says delivered.", "not_received", None),
    ("Saree ka colour photo se alag hai, mujhe return karna hai.", "return", None),
    ("Mujhe paise wapas chahiye.", "return", None),
    ("I want to return the saree, order four eight two three.", "return", "4823"),
    ("Dupatta phata hua aaya hai.", "damaged", None),
    ("Mujhe galat size bhej diya.", "damaged", None),
    ("The product is damaged.", "damaged", None),
    ("Mujhe apna order cancel karna hai.", "cancel", None),
    ("Please cancel order four eight two four.", "cancel", "4824"),
    ("Mera address change karna hai.", "address", None),
    ("Mujhe kisi insaan se baat karni hai.", "human", None),
    ("Seller se baat karwa dijiye.", "human", None),
    ("Theek hai, dhanyavaad.", "bye", None),
    ("Okay thank you, bye.", "bye", None),
]

HOLDOUT = [
    ("Bhaiya mera order abhi kidhar hai?", "status", None),
    ("Kurti kab tak deliver ho jaayegi?", "status", None),
    ("Order number chaar aath do ek track karna hai.", "status", "4821"),
    ("Hi, I just wanted to check the delivery date of my order.", "status", None),
    ("Mere order ka kya update hai?", "status", None),
    ("App mein delivered likha hai lekin parcel mere paas nahi aaya.", "not_received", None),
    ("Mujhe abhi tak koi parcel receive nahi hua.", "not_received", None),
    ("Courier wala bol raha hai de diya, par maine kuch nahi liya.", "not_received", None),
    ("My package was marked delivered but I didn't get it.", "not_received", None),
    ("Yeh bedsheet mujhe pasand nahi aayi, wapas karni hai.", "return", None),
    ("Refund kab milega? Main saree return karna chahta hoon.", "return", None),
    ("Order four eight two three ka refund chahiye.", "return", "4823"),
    ("Can I exchange this for a bigger size?", "return", None),
    ("Saree ka pallu fata hua hai.", "damaged", None),
    ("Bedsheet pe daag hai, bilkul ganda aaya hai.", "damaged", None),
    ("You sent me the wrong colour.", "damaged", None),
    ("Packet khola toh andar kuch aur hi tha.", "damaged", None),
    ("Dupatta wala order radd kar dijiye.", "cancel", None),
    ("I don't want it anymore, please cancel.", "cancel", None),
    ("Cancel karna hai order chaar aath do chaar.", "cancel", "4824"),
    ("Delivery ka pata badalna hai, naya address dena hai.", "address", None),
    ("Kya main delivery address update kar sakti hoon?", "address", None),
    ("Mujhe owner se baat karni hai.", "human", None),
    ("Please connect me to a real person.", "human", None),
    ("Mujhe call back chahiye.", "human", None),
    ("Bas itna hi poochna tha, shukriya.", "bye", None),
    ("Thank you so much, rakhta hoon.", "bye", None),
    ("Achha theek hai, bye bye.", "bye", None),
]

VOICES = ["Riyaa", "Devansh", "Shubham", "Kalpana", "Yashraj", "Avinash", "Chetana", "Tarika", "Prakash", "Lakshmi"]
