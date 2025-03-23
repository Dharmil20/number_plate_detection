import { useState, useEffect } from "react";
import axios from "axios";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [processedImage, setProcessedImage] = useState(null);
  const [croppedPlate, setCroppedPlate] = useState([]);
  const [plateText, setPlateText] = useState("");

  useEffect(() => {
    fetchAPI();
  }, []);

  const fetchAPI = async () => {
    try {
      await axios.get("http://127.0.0.1:5000");
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert("Please select a file first!");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile); // Ensure this key matches Flask backend

    try {
      const response = await axios.post("http://127.0.0.1:5000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setUploadedImage(response.data.uploaded_image);
      setProcessedImage(response.data.processed_image);
      setCroppedPlate(response.data.detections.map(obj => obj.cropped_plate));

      // Access the first element of the detections array to get extracted_text
      if (response.data.detections.length > 0) {
        setPlateText(response.data.detections[0].extracted_text);
      }

      console.log(response.data.detections[0].extracted_text); // Log the extracted text
      console.log(response);
    } catch (error) {
      console.error("Error uploading file:", error);
    }
  };

  return (
    <div className="bg-gray-800 text-gray-100 min-h-screen">
      {/* Navigation Bar */}
      <nav className="bg-gray-900 text-white py-4">
        <div className="container mx-auto px-4">
          <h1 className="text-2xl font-semibold">iLovePlates</h1>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        <div className="bg-gray-700 p-6 rounded-lg shadow-lg">
          <input
            type="file"
            className="block w-full text-gray-100 border border-gray-600 p-2 rounded-md bg-gray-900"
            onChange={handleFileChange}
          />
          <button
            onClick={handleUpload}
            className="mt-4 bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-lg"
          >
            Upload
          </button>
        </div>
      </div>

      {uploadedImage && (
        <div className="container mx-auto px-4 py-8">
          <h2 className="text-xl font-bold mb-4">Uploaded & Processed Images</h2>
          <div className="grid grid-cols-2 gap-4">
            <img
              src={`http://127.0.0.1:5000/static/upload/${uploadedImage}`}
              alt="Uploaded"
              className="rounded shadow-md"
            />
            <img
              src={`http://127.0.0.1:5000/static/predict/${processedImage}`}
              alt="Processed"
              className="rounded shadow-md"
            />
          </div>
        </div>
      )}

      {croppedPlate.length > 0 && (
        <div className="container mx-auto px-4 py-8">
          <h2 className="text-xl font-bold mb-4">Cropped License Plate</h2>
          <div className="flex justify-center">
            {croppedPlate.map((plate, index) => (
              <img
                key={index}
                src={`http://127.0.0.1:5000/static/roi/${plate}`}
                alt={`Cropped Plate ${index + 1}`}
                className="rounded shadow-md"
              />
            ))}
          </div>
        </div>
      )}

      {plateText && (
        <div className="container mx-auto px-4 py-8">
          <h2 className="text-xl font-bold">Extracted License Plate Text</h2>
          <div className="bg-green-500 text-white p-4 rounded-md text-lg font-semibold">
            {plateText}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;