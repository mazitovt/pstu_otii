import uvicorn
from fastapi import FastAPI, File, UploadFile
import json
from simple_face_recognizer import SimpleFaceRecognizer


def load_json(json_file_path):
    """Читает данные из json файла"""
    with open(json_file_path, "r") as conf_file:
        return json.load(conf_file)


app = FastAPI()
sfr = SimpleFaceRecognizer(load_json("appconf.json"))


@app.get("/knownpeople/")
async def get_known_people():
    sfr.load_new_images()
    return {"known_people": f"{sfr.known_faces()}"}


@app.post("/uploadphoto/")
async def upload_photo(name: str, photo: UploadFile = File(...)):
    contents = await photo.read()

    try:
        if sfr.add_person(name, contents):
            result = f"person {name} with photo {photo.filename} uploaded"
        else:
            result = "not one person"
    except:
        result = "error occurred"

    return {"upload_result": result}


@app.post("/checkphoto/")
async def check_photo(photo: UploadFile = File(...)):
    contents = await photo.read()

    sfr.load_new_images()

    if len(sfr.known_faces()) > 0:
        try:
            result = sfr.detect_known_faces(contents)
        except:
            result = "error occurred"
    else:
        result = "no known people in database"

    return {"check_result": f"{result}"}


if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")
