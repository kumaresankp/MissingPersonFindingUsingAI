from django.shortcuts import render,redirect
from .models import* 
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import datetime
import face_recognition
import cv2
from twilio.rest import Client
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
import numpy as np
#Add yourr own credentials
account_sid = 'ACe2a25987f589b646e9fad8859f1e8f14'
auth_token = 'de1b84a6c3293c2a80c2976b4943b6b9'
twilio_whatsapp_number = '+18286629608'

# Create your views here.
def home(request):
    return render(request,"index.html")

def send_whatsapp_message(to,context):
    client = Client(account_sid, auth_token)
    whatsapp_message = (
    f"Dear {context['fathers_name']},\n\n"
    f"We are pleased to inform you that the missing person missing from {context['missing_from']} and you were concerned about has been found. "
    "The person was located in a camera footage, and we have identified their whereabouts.\n\n"
    "Here are the details:\n"
    f" - Name: {context['first_name']} {context['last_name']}\n"
    f" - Date and Time of Sighting: {context['date_time']}\n"
    f" - Location: {context['location']}\n"
    f" - Aadhar Number: {context['aadhar_number']}\n\n"
    #"We understand the relief this news must bring to you. If you have any further questions or require more information, please do not hesitate to reach out to us.\n\n"
    "Thank you for your cooperation and concern in this matter.\n\n"
    "Sincerely,\n\n"
    "Team FindMyPerson ")
    message = client.messages.create(
        body=whatsapp_message,
        from_=twilio_whatsapp_number,
        to=to
    )

    print(f"WhatsApp message sent: {message.sid}")


# Load OpenCV's built-in face detection model (Haar Cascade)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize the LBPH face recognizer
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

# Store labels and images
labels = []
faces = []
label_dict = {}


def train_model():
    global labels, faces, label_dict
    labels.clear()
    faces.clear()
    label_dict.clear()
    
    for idx, person in enumerate(MissingPerson.objects.all()):
        try:
            image = cv2.imread(person.image.path, cv2.IMREAD_GRAYSCALE)
            if image is not None:
                faces.append(image)
                labels.append(idx)
                label_dict[idx] = person  # Store person details
                print(f"Loaded {person.first_name} {person.last_name}")
            else:
                print(f"Warning: Couldn't read image for {person.first_name} {person.last_name}")

        except Exception as e:
            print(f"Error loading {person.image.path}: {e}")

    if faces:
        print("Training face recognizer with", len(faces), "faces.")
        face_recognizer.train(faces, np.array(labels))
    else:
        print("No faces found for training!")

train_model()# Train the model before starting detection

def detect(request):
    video_capture = cv2.VideoCapture(0)
    face_detected = False

    while True:
        ret, frame = video_capture.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
        
        # Detect faces in the frame
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]  # Extract face region
            
            # Recognize face using LBPH model
            label, confidence = face_recognizer.predict(roi_gray)
            
            if confidence < 80:  # Confidence threshold (adjustable)
                person = label_dict.get(label, None)
                if person:
                    name = f"{person.first_name} {person.last_name}"
                    
                    if not face_detected:
                        print(f"Hi {name} is found")
                        
                        recipient_phone_number = f'+91{person.phone_number}'
                        context = {
                            "first_name": person.first_name, "last_name": person.last_name,
                            "fathers_name": person.father_name, "aadhar_number": person.aadhar_number,
                            "missing_from": person.missing_from, "date_time": datetime.now().strftime('%d-%m-%Y %H:%M'),
                            "location": "India"
                        }
                        
                        send_whatsapp_message(recipient_phone_number, context)
                        html_message = render_to_string('findemail.html', context=context)
                        send_mail('Missing Person Found', '', 'pptodo01@gmail.com', [person.email], 
                                  fail_silently=False, html_message=html_message)
                        face_detected = True

            else:
                name = "Unknown"

            # Draw face rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow('Camera Feed', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    return render(request, "surveillance.html")

def surveillance(request):
    return render(request,"surveillance.html")


def register(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        father_name = request.POST.get('fathers_name')
        date_of_birth = request.POST.get('dob')
        address = request.POST.get('address')
        phone_number = request.POST.get('phonenum')
        aadhar_number = request.POST.get('aadhar_number')
        missing_from = request.POST.get('missing_date')
        email = request.POST.get('email')
        image = request.FILES.get('image')
        gender = request.POST.get('gender')
        aadhar = MissingPerson.objects.filter(aadhar_number=aadhar_number)
        if aadhar.exists():
            messages.info(request, 'Aadhar Number already exists')
            return redirect('/register')
        person = MissingPerson.objects.create(
            first_name = first_name,
            last_name = last_name,
            father_name = father_name,
            date_of_birth = date_of_birth,
            address = address,
            phone_number = phone_number,
            aadhar_number = aadhar_number,
            missing_from = missing_from,
            email = email,
            image = image,
            gender = gender,
        )
        person.save()
        messages.success(request,'Case Registered Successfully')
        current_time = datetime.now().strftime('%d-%m-%Y %H:%M')
        subject = 'Case Registered Successfully'
        from_email = 'pptodo01@gmail'
        recipientmail = person.email
        context = {"first_name":person.first_name,"last_name":person.last_name,
                    'fathers_name':person.father_name,"aadhar_number":person.aadhar_number,
                    "missing_from":person.missing_from,"date_time":current_time}
        html_message = render_to_string('regmail.html',context = context)
        # Send the email
        send_mail(subject,'', from_email, [recipientmail], fail_silently=False, html_message=html_message)

    return render(request,"register.html")


def  missing(request):
    queryset = MissingPerson.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(aadhar_number__icontains=search_query)
    
    context = {'missingperson': queryset}
    return render(request,"missing.html",context)

def delete_person(request, person_id):
    person = get_object_or_404(MissingPerson, id=person_id)
    person.delete()
    return redirect('missing')  # Redirect to the missing view after deleting


def update_person(request, person_id):
    person = get_object_or_404(MissingPerson, id=person_id)

    if request.method == 'POST':
        # Retrieve data from the form
        first_name = request.POST.get('first_name', person.first_name)
        last_name = request.POST.get('last_name', person.last_name)
        fathers_name = request.POST.get('fathers_name', person.father_name)
        dob = request.POST.get('dob', person.date_of_birth)
        address = request.POST.get('address', person.address)
        email = request.POST.get('email', person.email)
        phonenum = request.POST.get('phonenum', person.phone_number)
        aadhar_number = request.POST.get('aadhar_number', person.aadhar_number)
        missing_date = request.POST.get('missing_date', person.missing_from)
        gender = request.POST.get('gender', person.gender)

        # Check if a new image is provided
        new_image = request.FILES.get('image')
        if new_image:
            person.image = new_image

        # Update the person instance
        person.first_name = first_name
        person.last_name = last_name
        person.father_name = fathers_name
        person.date_of_birth = dob
        person.address = address
        person.email = email
        person.phone_number = phonenum
        person.aadhar_number = aadhar_number
        person.missing_from = missing_date
        person.gender = gender

        # Save the changes
        person.save()

        return redirect('missing')  # Redirect to the missing view after editing

    return render(request, 'edit.html', {'person': person})


def found(request):
    pass