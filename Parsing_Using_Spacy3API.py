
import datetime
import imaplib
import difflib
import pymongo
import email
import spacy
import re 
import io
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from googletrans import Translator
from pymongo import MongoClient
from PyPDF2 import PdfReader


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

translator = Translator()
nlp = spacy.load("en_core_web_sm")



#--------------------------------------------------------------------------------------------------------------------------------------------


# Email connection details
imap_server = "imap.gmail.com"
username = "sarramz2002@gmail.com"
password = "mxavwddhvgfeqlxr"
errorMessage= ""
connection_string = "mongodb+srv://sarramz:23466957@cluster0.fnjtmtz.mongodb.net/?retryWrites=true&w=majority"

# create a MongoDB client object
client = MongoClient(connection_string)
# test the connection by accessing a collection from the database
db = client["PFE"]
id_list = [str(job['_id']) for job in db.jobs.find({}, {"_id": 1})]


#--------------------------------------------------------------------------------------------------------------------------------------------


def save_attachments(part,email_message):

    subject = email_message["Subject"]
    phone_regex = r"\+216 ?\d{8}|\d{2}\s\d{3}\s\d{3}|\d{2}\s\d{2}\s\d{2}\s\d{2}|\d[\d ]{0,6}\d$"

    doc = {
    "filename": part.get_filename(),
    "attachment": part.get_payload(decode=True),
    "sender_name": email.utils.parseaddr(email_message["From"])[0],
    "sender_email": email.utils.parseaddr(email_message["From"])[1],
    "sent_time": None  # Placeholder for the sent time
}

    sent_date = email.utils.parsedate_to_datetime(email_message["Date"])
    if sent_date:
        doc["sent_time"] = sent_date.strftime("%Y-%m-%d")  # Format the sent time as desired


    pdf_content = part.get_payload(decode=True)
    
    file = io.BytesIO(pdf_content)
    reader = PdfReader(file)
    number_of_pages = len(reader.pages)
    text=""

    for page_num in range(number_of_pages):
        # get the current page object
        page = reader.pages[page_num]

        # extract the text from the page and add it to the overall text string
        text = text+page.extract_text()

    collection_name = None
    if "pfe" in subject.lower():
        collection_name = "pfe_candidates"
    elif "stage" in subject.lower():
        collection_name = "stage_candidates"
    elif re.match(r"^[0-9a-f]{24}$", subject):
        collection_name = "candidates"
        if(subject in id_list):
            doc['wanted_job']=subject
      
    if collection_name :

        cleared_text=getCleaned_text(text)
       
        Number = re.findall(phone_regex, text)
        if len(Number) == 0:
            Number = re.findall(phone_regex, cleared_text)
            if len(Number) == 0:
                Number = ''
            else : 
                Number = re.findall(phone_regex, cleared_text)[0]
        
        if(str(type(Number))!="<class 'str'>"):
            if len(Number) != 0:
                doc['Number']=Number[0]
            else : 
                Number = ''
        else :
            doc['Number']=Number
       
        doc['data']=getCvData(cleared_text)
        doc['job_scores']=[]
        
        # Insert the file into MongoDB
        try:
             
            collection = db[collection_name]
            collection.insert_one(doc)
        except pymongo.errors.OperationFailure as e:
            errorMessage= f"Unable to connect to MongoDB cloud: {e}" 
        except Exception as e:
            errorMessage= f"An unexpected error occurred: {e}"

        return True
    else:
        return False
    
    
#--------------------------------------------------------------------------------------------------------------------------------------------   


@app.get("/")
def read_root():
    return {"Message": "Python API"}

      
#--------------------------------------------------------------------------------------------------------------------------------------------


@app.post("/TestConnection")
async def test_connection(request: Request):
    try:
        # Extract username and password from request body
        data = await request.json()
        username1 = data.get('username')
        password1 = data.get('password')
        # Connect to the email server
        imap_server = "imap.gmail.com"
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username1, password1)
        mail.logout()  # Close the connection
        return {'connected': True}
    except Exception as e:
        return {'connected': False}


#--------------------------------------------------------------------------------------------------------------------------------------------


@app.get("/CheckCvDataFromMail")
async def check_email():
    try:
        savedfiles=0
        # Connect to the email server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        mail.select("inbox")
        

        criteria = "(UNSEEN)"
        type, data = mail.search(None, criteria)
        for num in data[0].split():
            typ, data = mail.fetch(num, "(RFC822)")
            raw_email = data[0][1]
            # converts byte literal to string removing b''
            raw_email_string = raw_email.decode("utf-8")  # type: ignore
            email_message = email.message_from_string(raw_email_string)
            has_attachment = False
            # downloading attachments
            for part in email_message.walk():
                if part.get_content_type() == "application/pdf":
                    if part.get_content_maintype() == "multipart":
                        continue
                    if part.get("Content-Disposition") is None:
                        continue
                    fileName = part.get_filename()
                    if bool(fileName):
                        has_attachment = True
                        if (save_attachments(part,email_message))==False:
                            mail.store(num, "-FLAGS", "\\Seen")
                        else:
                            savedfiles=savedfiles+1
            if has_attachment == False:
                mail.store(num, "-FLAGS", "\\Seen")
        mail.logout()
        return {'success': True, 'newCVS': savedfiles}
    except Exception as e:
        return {'success': False, 'message': str(e)}

    
#--------------------------------------------------------------------------------------------------------------------------------------------


@app.post("/CheckCvDataFromMail")
async def check_email(request: Request):
    try:
        # Extract username and password from request body
        data = await request.json()
        username1 = data.get('username')
        password1 = data.get('password')
        
        savedfiles=0
        # Connect to the email server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username1, password1)
        mail.select("inbox")
        

        criteria = "(UNSEEN)"
        type, data = mail.search(None, criteria)
        for num in data[0].split():
            typ, data = mail.fetch(num, "(RFC822)")
            raw_email = data[0][1]
            # converts byte literal to string removing b''
            raw_email_string = raw_email.decode("utf-8")  # type: ignore
            email_message = email.message_from_string(raw_email_string)
            has_attachment = False
            # downloading attachments
            for part in email_message.walk():
                if part.get_content_type() == "application/pdf":
                    if part.get_content_maintype() == "multipart":
                        continue
                    if part.get("Content-Disposition") is None:
                        continue
                    fileName = part.get_filename()
                    if bool(fileName):
                        has_attachment = True
                        if (save_attachments(part,email_message))==False:
                            mail.store(num, "-FLAGS", "\\Seen")
                        else:
                            savedfiles=savedfiles+1
            if has_attachment == False:
                mail.store(num, "-FLAGS", "\\Seen")
        mail.logout()
        return {'success': True, 'newCVS': savedfiles}
    except Exception as e:
        return {'success': False, 'message': str(e)}

    
#--------------------------------------------------------------------------------------------------------------------------------------------


def getCleaned_text(results):
    
    # Translate the text to English using Googletrans
    translator = Translator()
    try:
        text = translator.translate(results, dest="en").text
    except :
        text = results
        
    # Clean and preprocess the text using spaCy
    if type(text) == str:
        text = text.replace('\n', ' ')
        text = text.encode('ascii', 'ignore').decode()
        doc = nlp(text)
        cleaned_text = ' '.join([token.lemma_ for token in doc if not token.is_stop and not token.is_punct and not token.is_space]).strip()
        return cleaned_text
    else:
        return ""


#--------------------------------------------------------------------------------------------------------------------------------------------


def getCvData(cleared_text):
    nlp = spacy.load("model-best")  
    doc = nlp(cleared_text)
    Years_of_Experience_Data =[]

    entities =  {"College_Name":[],
                    "Companies_Worked_At":[],
                    "Degree":[],
                    "Email_Address":[],
                    "Languages":[],
                    "Name":[],
                    "Skills":[],
                    "Years_of_Experience":0,
                    }

    for ent in doc.ents:
            if ent.label_ == "Years_of_Experience":
                Years_of_Experience_Data.append(ent.text)
            else:
                if ent.text not in entities[ent.label_]:
                    entities[ent.label_].append(ent.text)

         
    entities["Years_of_Experience"]=calculate_total_experience(Years_of_Experience_Data)
    return(dict(entities))


#--------------------------------------------------------------------------------------------------------------------------------------------


def calculate_total_experience(years_of_experience_data):
    total_experience = 0
    is_working = False  # Assuming the current year is 2023
    years=[]
    for experience_string in years_of_experience_data:
        if "experience" in experience_string:
            # Extract the number of years mentioned in the sentence containing "experience"
            experience_match = re.search(r'\b(\d+)\b', experience_string)
            if experience_match:
                total_experience = int(experience_match.group(1))
                return total_experience
        else:
            # Extract start year and end year
            years.extend(re.findall(r'\b(19\d{2}|20\d{2})\b', experience_string))
            if ("aujourd'hui" in experience_string.lower() or "today" in experience_string.lower()):
                is_working = True

    if years:
            if (is_working):
                diff =  datetime.datetime.now().year - int(min(years))
            else:
                diff = int(max(years)) - int(min(years))
    else:
            diff = 0
   
    total_experience=diff

    return total_experience


#--------------------------------------------------------------------------------------------------------------------------------------------



