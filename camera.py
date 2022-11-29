from datetime import datetime
from providers import PROVIDERS
import os
import smtplib
import ssl
import time
import cv2

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from os.path import basename

from dotenv import load_dotenv

# TODO: Clean imports

# Person detection function created by Tech with Tim (https://www.youtube.com/watch?v=Exic9E5rNok)


def detect_person(
    SECONDS_TILL_STOP: int = 10,
    frame_num: int = 20,
    face_accuracy: float = 1.1,
    body_accuracy: float = 1.1,
    face_neighbors: int = 5,
    body_neighbors: int = 5,
    show_camera: bool = True,
    camera_name: int = 0,
    frame_size: tuple = (640, 480)
):
    cap = cv2.VideoCapture(camera_name)

    face_cascade = cv2.CascadeClassifier(
        os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    body_cascade = cv2.CascadeClassifier(
        os.path.join(cv2.data.haarcascades, "haarcascade_fullbody.xml"))

    detection: bool = False
    detection_stopped_time: bool = None
    timer_started: bool = False

    frame_count: int = 0
    frame_time = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")

    fourCC = cv2.VideoWriter_fourcc(*"mp4v")

    while True:
        _, frame = cap.read()

        # Save frame
        if frame_count == frame_num:
            cv2.imwrite(f"./{frame_time}.jpg", frame)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, face_accuracy, face_neighbors)
        bodies = body_cascade.detectMultiScale(
            gray, body_accuracy, body_neighbors)

        if len(faces) + len(bodies) > 0:
            if detection:
                timer_started = False
            else:
                detection = True
                current_time = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
                out = cv2.VideoWriter(
                    f"{current_time}.mp4", fourCC, 30, frame_size)
                print("Started recording")
        elif detection:
            if timer_started:
                if detection_stopped_time != None and \
                        time.time() - detection_stopped_time >= SECONDS_TILL_STOP:
                    detection = False
                    timer_started = False
                    detection_stopped_time = None
                    out.release()
                    time.sleep(1)
                    send_recording(
                        os.getenv('NUMBER'),
                        "Sending screenshot.",
                        f"./{frame_time}.jpg",
                        "image",
                        "jpg",
                        os.getenv('PROVIDER'),
                        os.getenv('PROVIDER_SCHEMA'),
                        (os.getenv('EMAIL'), os.getenv('PASSWORD')),
                        "Face/Body detected"
                    )
                    print("Stopped recording")
            else:
                timer_started = True
                detection_stopped_time = time.time()

        if detection:
            out.write(frame)

        for (x, y, width, height) in faces:
            cv2.rectangle(frame, (x, y), (x + width,
                          y + height), (255, 0, 0), 3)

        for (x, y, width, height) in bodies:
            cv2.rectangle(frame, (x, y), (x + width,
                          y + height), (0, 0, 255), 3)

        if show_camera:
            cv2.imshow("Camera", frame)

        frame_count += 1

        if cv2.waitKey(1) == ord('q'):
            break

    out.release()
    cap.release()
    cv2.destroyAllWindows()

# Message sending function created by Alfredo Sequeida (https://www.youtube.com/watch?v=4-ysecoraKo)


def send_recording(
    number: str,
    message: str,
    file_path: str,
    mime_maintype: str,
    mime_subtype: str,
    provider: str,
    provider_schema: str,
    sender_credentials: tuple,
    subject: str = "Default Subject",
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465
):
    sender_email, email_password = sender_credentials
    receiver_email = f"{number}@{PROVIDERS.get(provider).get(provider_schema)}"

    email_message = MIMEMultipart()
    email_message["Subject"] = subject
    email_message["From"] = sender_email
    email_message["To"] = receiver_email

    email_message.attach(MIMEText(message, "plain"))

    with open(file_path, "rb") as attachment:
        part = MIMEBase(mime_maintype, mime_subtype)
        part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={basename(file_path)}",
        )

        email_message.attach(part)

    text = email_message.as_string()

    with smtplib.SMTP_SSL(
        smtp_server, smtp_port, context=ssl.create_default_context()
    ) as email:
        email.login(sender_email, email_password)
        email.sendmail(sender_email, receiver_email, text)


if __name__ == "__main__":
    load_dotenv(dotenv_path="./config.env")
    detect_person()
