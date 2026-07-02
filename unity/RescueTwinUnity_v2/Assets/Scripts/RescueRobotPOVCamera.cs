using UnityEngine;

public class RescueRobotPOVCamera : MonoBehaviour
{
    [Header("Referencias")]
    public Transform targetRobot;
    public Camera mainCamera;
    public Camera povCamera;

    [Header("Tecla")]
    public KeyCode toggleKey = KeyCode.V;

    [Header("Ajustes POV")]
    public Vector3 povLocalPosition = new Vector3(0f, 0.75f, 0.95f);
    public Vector3 povLocalRotation = new Vector3(10f, 0f, 0f);
    public float povFieldOfView = 75f;

    [Header("Estado")]
    public bool startInPOV = false;

    private bool isPOV = false;

    private void Start()
    {
        Setup();
    }

    private void Update()
    {
        if (Input.GetKeyDown(toggleKey))
        {
            ToggleCamera();
        }

        UpdatePOVCameraTransform();
    }

    [ContextMenu("Setup POV Camera")]
    public void Setup()
    {
        FindReferences();

        if (targetRobot == null)
        {
            Debug.LogWarning("RescueRobotPOVCamera: no encontré el Robot. No se activa POV.");
            EnableMainCameraOnly();
            return;
        }

        if (povCamera == null)
        {
            CreatePOVCamera();
        }

        isPOV = startInPOV;
        ApplyCameraState();
    }

    private void FindReferences()
    {
        if (mainCamera == null)
        {
            mainCamera = Camera.main;
        }

        if (mainCamera == null)
        {
            GameObject mainCamObj = GameObject.Find("Main Camera");

            if (mainCamObj != null)
                mainCamera = mainCamObj.GetComponent<Camera>();
        }

        if (targetRobot == null)
        {
            GameObject robotObj = GameObject.Find("Robot");

            if (robotObj != null)
                targetRobot = robotObj.transform;
        }
    }

    private void CreatePOVCamera()
    {
        GameObject old = GameObject.Find("Robot_POV_Camera");

        if (old != null)
        {
            if (Application.isPlaying) Destroy(old);
            else DestroyImmediate(old);
        }

        GameObject camObject = new GameObject("Robot_POV_Camera");
        camObject.transform.SetParent(targetRobot, false);

        povCamera = camObject.AddComponent<Camera>();

        povCamera.enabled = false;
        povCamera.fieldOfView = povFieldOfView;
        povCamera.nearClipPlane = 0.03f;
        povCamera.farClipPlane = 120f;
        povCamera.depth = 100;
        povCamera.targetDisplay = 0;
        povCamera.clearFlags = CameraClearFlags.Skybox;

        AudioListener listener = camObject.GetComponent<AudioListener>();

        if (listener != null)
        {
            if (Application.isPlaying) Destroy(listener);
            else DestroyImmediate(listener);
        }

        UpdatePOVCameraTransform();
    }

    private void UpdatePOVCameraTransform()
    {
        if (povCamera == null || targetRobot == null)
            return;

        povCamera.transform.localPosition = povLocalPosition;
        povCamera.transform.localRotation = Quaternion.Euler(povLocalRotation);
        povCamera.fieldOfView = povFieldOfView;
    }

    private void ToggleCamera()
    {
        FindReferences();

        if (targetRobot == null)
        {
            Debug.LogWarning("No hay robot para POV. Mantengo cámara general.");
            EnableMainCameraOnly();
            return;
        }

        if (povCamera == null)
        {
            CreatePOVCamera();
        }

        if (povCamera == null)
        {
            Debug.LogWarning("No se pudo crear cámara POV. Mantengo cámara general.");
            EnableMainCameraOnly();
            return;
        }

        isPOV = !isPOV;
        ApplyCameraState();
    }

    private void ApplyCameraState()
    {
        if (mainCamera == null)
        {
            FindReferences();
        }

        if (povCamera == null)
        {
            EnableMainCameraOnly();
            return;
        }

        if (isPOV)
        {
            if (mainCamera != null)
                mainCamera.enabled = false;

            povCamera.gameObject.SetActive(true);
            povCamera.enabled = true;

            Debug.Log("Cámara POV del robot activada.");
        }
        else
        {
            EnableMainCameraOnly();
            Debug.Log("Cámara general activada.");
        }
    }

    private void EnableMainCameraOnly()
    {
        if (mainCamera == null)
            FindReferences();

        if (mainCamera != null)
        {
            mainCamera.gameObject.SetActive(true);
            mainCamera.enabled = true;
        }

        if (povCamera != null)
        {
            povCamera.enabled = false;
        }

        isPOV = false;
    }
}