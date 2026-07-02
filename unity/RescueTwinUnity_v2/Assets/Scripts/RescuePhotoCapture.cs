using System;
using System.Globalization;
using System.IO;
using UnityEngine;

public class RescuePhotoCapture : MonoBehaviour
{
    [Header("Referencias")]
    public Transform targetRobot;
    public Camera activeCamera;

    [Header("Tecla")]
    public KeyCode captureKey = KeyCode.C;

    [Header("Configuración")]
    public string exportFolderName = "Exports";
    public string imageFolderName = "robot_captures";
    public string csvFileName = "photo_evidence.csv";

    [Header("Mensaje en pantalla")]
    public float messageDuration = 1.8f;

    private string exportPath;
    private string imagePath;
    private string csvPath;

    private string lastMessage = "";
    private float messageTimer = 0f;
    private int captureCounter = 0;

    private void Start()
    {
        Setup();
    }

    private void Update()
    {
        if (Input.GetKeyDown(captureKey))
        {
            CapturePhotoEvidence();
        }

        if (messageTimer > 0f)
        {
            messageTimer -= Time.deltaTime;
        }
    }

    [ContextMenu("Setup Photo Capture")]
    public void Setup()
    {
        if (targetRobot == null)
        {
            GameObject robotObj = GameObject.Find("Robot");

            if (robotObj != null)
                targetRobot = robotObj.transform;
        }

        if (activeCamera == null)
        {
            activeCamera = Camera.main;
        }

        // Carpeta afuera de Assets:
        // RescueTwinUnity_v2/Exports
        exportPath = Path.GetFullPath(
            Path.Combine(Application.dataPath, "..", exportFolderName)
        );

        imagePath = Path.Combine(exportPath, imageFolderName);
        csvPath = Path.Combine(exportPath, csvFileName);

        Directory.CreateDirectory(exportPath);
        Directory.CreateDirectory(imagePath);

        EnsureCsvHeader();

        Debug.Log("Carpeta de exportación: " + exportPath);
        Debug.Log("Carpeta de fotos: " + imagePath);
        Debug.Log("CSV de evidencia: " + csvPath);
    }

    private void CapturePhotoEvidence()
    {
        if (string.IsNullOrEmpty(exportPath))
        {
            Setup();
        }

        captureCounter++;

        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");

        string fileName =
            "robot_photo_" +
            timestamp +
            "_" +
            captureCounter.ToString("000") +
            ".png";

        string fullImagePath = Path.Combine(imagePath, fileName);

        ScreenCapture.CaptureScreenshot(fullImagePath);

        Vector3 robotPosition = Vector3.zero;

        if (targetRobot != null)
            robotPosition = targetRobot.position;

        string cameraName = "UnknownCamera";

        if (activeCamera != null)
            cameraName = activeCamera.name;
        else if (Camera.main != null)
            cameraName = Camera.main.name;

        string csvLine =
            DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "," +
            fileName + "," +
            robotPosition.x.ToString("F2", CultureInfo.InvariantCulture) + "," +
            robotPosition.y.ToString("F2", CultureInfo.InvariantCulture) + "," +
            robotPosition.z.ToString("F2", CultureInfo.InvariantCulture) + "," +
            cameraName + "," +
            "visual_evidence";

        File.AppendAllText(csvPath, csvLine + Environment.NewLine);

        lastMessage = "FOTO CAPTURADA";
        messageTimer = messageDuration;

        Debug.Log("Foto capturada en: " + fullImagePath);
        Debug.Log("CSV actualizado en: " + csvPath);
    }

    private void EnsureCsvHeader()
    {
        if (File.Exists(csvPath))
            return;

        string header =
            "timestamp,image_file,robot_x,robot_y,robot_z,camera_name,evidence_type";

        File.WriteAllText(csvPath, header + Environment.NewLine);
    }

    private void OnGUI()
    {
        if (messageTimer <= 0f)
            return;

        GUIStyle style = new GUIStyle(GUI.skin.box);
        style.fontSize = 30;
        style.fontStyle = FontStyle.Bold;
        style.normal.textColor = Color.white;
        style.alignment = TextAnchor.MiddleCenter;

        Rect rect = new Rect(
            Screen.width * 0.5f - 170f,
            Screen.height - 80f,
            340f,
            46f
        );

        GUI.Box(rect, lastMessage, style);
    }
}