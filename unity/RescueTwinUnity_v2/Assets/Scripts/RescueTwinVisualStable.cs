using System.Collections;
using UnityEngine;
using UnityEngine.Rendering;

public class RescueRobotVisualStable : MonoBehaviour
{
    [Header("Referencia")]
    public Transform targetRobot;
    public float startDelay = 0.25f;

    [Header("Ajustes generales")]
    public Vector3 visualOffset = new Vector3(0f, 0.02f, 0f);
    public Vector3 visualRotation = new Vector3(0f, 0f, 0f);
    public float visualScale = 1.0f;

    [Header("Ocultar visual original")]
    public bool forceHideOriginalEveryFrame = true;
    public bool keepSmallOriginalLegs = true;

    [Header("Patas originales visibles")]
    public float legVisibilityHeight = 0.34f;
    public float footHeight = 0.09f;
    public float maxVisibleLegPartSize = 0.55f;

    [Header("Estilo rescate")]
    public Color bodyColor = new Color(0.05f, 0.16f, 0.38f);
    public Color rescueYellow = new Color(0.98f, 0.72f, 0.08f);
    public Color darkColor = new Color(0.08f, 0.08f, 0.09f);
    public Color metalColor = new Color(0.48f, 0.49f, 0.50f);
    public Color lightMetalColor = new Color(0.72f, 0.72f, 0.74f);
    public Color sensorColor = new Color(0.08f, 0.95f, 1.0f);
    public Color medicalRed = new Color(0.95f, 0.06f, 0.04f);
    public Color whiteColor = new Color(0.94f, 0.94f, 0.92f);
    public Color statusColor = Color.green;

    [Header("Luces")]
    public bool addLights = true;
    public float sensorLightIntensity = 0.55f;
    public float statusLightIntensity = 0.75f;
    public float lightRange = 1.6f;

    private Material bodyMat;
    private Material yellowMat;
    private Material darkMat;
    private Material metalMat;
    private Material lightMetalMat;
    private Material blackMat;
    private Material whiteMat;
    private Material redMat;
    private Material cyanLightMat;
    private Material statusLightMat;

    private Transform visualRoot;
    private Renderer statusRenderer;
    private Light statusLight;

    private IEnumerator Start()
    {
        yield return new WaitForSeconds(startDelay);
        BuildOrRefresh();
    }

    private void LateUpdate()
    {
        if (forceHideOriginalEveryFrame && targetRobot != null)
        {
            HideOriginalVisuals();
        }
    }

    [ContextMenu("Build / Refresh Rescue Robot")]
    public void BuildOrRefresh()
    {
        if (targetRobot == null)
        {
            targetRobot = FindRobot();
        }

        if (targetRobot == null)
        {
            Debug.LogWarning("[RescueRobotVisualStable] No se encontró el robot. Arrastrá manualmente el objeto Robot al campo Target Robot.");
            return;
        }

        CreateMaterials();
        RemoveOldVisual();
        HideOriginalVisuals();
        BuildNewVisual();
        SetStatusColor(statusColor);

        Debug.Log("[RescueRobotVisualStable] Visual del robot reconstruido correctamente.");
    }

    private Transform FindRobot()
    {
        GameObject direct = GameObject.Find("Robot");

        if (direct != null)
            return direct.transform;

        GameObject rescue = GameObject.Find("RescueRobot");

        if (rescue != null)
            return rescue.transform;

        GameObject quadruped = GameObject.Find("QuadrupedRobot");

        if (quadruped != null)
            return quadruped.transform;

        GameObject[] all = Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include);

        foreach (GameObject go in all)
        {
            string n = go.name.ToLower();

            if (
                n.Contains("robot") ||
                n.Contains("dog") ||
                n.Contains("perro") ||
                n.Contains("quadruped") ||
                n.Contains("searchdog")
            )
            {
                if (go.GetComponentInChildren<Renderer>(true) != null)
                    return go.transform;
            }
        }

        return null;
    }

    private void RemoveOldVisual()
    {
        if (targetRobot == null)
            return;

        string[] oldNames =
        {
            "__RescueRobotVisualStable__",
            "__RescueRobotVisual__",
            "Rescue Robot Visual"
        };

        foreach (string oldName in oldNames)
        {
            Transform old = targetRobot.Find(oldName);

            if (old != null)
            {
                SafeDestroy(old.gameObject);
            }
        }
    }

    private void HideOriginalVisuals()
    {
        if (targetRobot == null)
            return;

        Renderer[] renderers = targetRobot.GetComponentsInChildren<Renderer>(true);

        foreach (Renderer r in renderers)
        {
            if (r == null)
                continue;

            if (visualRoot != null && r.transform.IsChildOf(visualRoot))
                continue;

            if (r.GetComponent<LineRenderer>() != null)
                continue;

            Vector3 localCenter = targetRobot.InverseTransformPoint(r.bounds.center);

            float maxSize = Mathf.Max(
                r.bounds.size.x,
                r.bounds.size.y,
                r.bounds.size.z
            );

            bool isLowEnough = localCenter.y < legVisibilityHeight;
            bool isSmallEnough = maxSize < maxVisibleLegPartSize;
            bool keepOriginalPart = keepSmallOriginalLegs && isLowEnough && isSmallEnough;

            r.enabled = keepOriginalPart;

            if (keepOriginalPart)
            {
                if (localCenter.y < footHeight)
                {
                    r.sharedMaterial = blackMat;
                }
                else
                {
                    r.sharedMaterial = lightMetalMat;
                }
            }
        }
    }

    private void BuildNewVisual()
    {
        GameObject root = new GameObject("__RescueRobotVisualStable__");
        root.transform.SetParent(targetRobot, false);
        root.transform.localPosition = visualOffset;
        root.transform.localRotation = Quaternion.Euler(visualRotation);
        root.transform.localScale = Vector3.one * visualScale;

        visualRoot = root.transform;

        BuildMainBody(root.transform);
        BuildTopRescuePanel(root.transform);
        BuildFrontSensorHead(root.transform);
        BuildStatusBeacon(root.transform);
        BuildMedicalBox(root.transform);
        BuildAntenna(root.transform);
        BuildSideRails(root.transform);
        BuildCompactLegs(root.transform);
        BuildRescueStripes(root.transform);
        BuildLights(root.transform);
    }

    private void BuildMainBody(Transform root)
    {
        CreateCube(
            root,
            "Body_Main_Blue",
            new Vector3(0f, 0.44f, 0f),
            new Vector3(0.68f, 0.24f, 0.92f),
            Vector3.zero,
            bodyMat
        );

        CreateCube(
            root,
            "Body_Under_Dark",
            new Vector3(0f, 0.30f, 0f),
            new Vector3(0.58f, 0.08f, 0.74f),
            Vector3.zero,
            darkMat
        );

        CreateCube(
            root,
            "Rear_Battery_Module",
            new Vector3(0f, 0.43f, -0.55f),
            new Vector3(0.50f, 0.18f, 0.14f),
            Vector3.zero,
            darkMat
        );
    }

    private void BuildTopRescuePanel(Transform root)
    {
        CreateCube(
            root,
            "Top_Rescue_Yellow",
            new Vector3(0f, 0.61f, 0.03f),
            new Vector3(0.48f, 0.08f, 0.52f),
            Vector3.zero,
            yellowMat
        );

        CreateCube(
            root,
            "Top_Black_Stripe",
            new Vector3(0f, 0.665f, 0.03f),
            new Vector3(0.12f, 0.025f, 0.55f),
            Vector3.zero,
            darkMat
        );
    }

    private void BuildFrontSensorHead(Transform root)
    {
        CreateCube(
            root,
            "Front_Head_Blue",
            new Vector3(0f, 0.44f, 0.54f),
            new Vector3(0.44f, 0.20f, 0.18f),
            Vector3.zero,
            bodyMat
        );

        CreateCube(
            root,
            "Camera_Frame_Dark",
            new Vector3(0f, 0.44f, 0.66f),
            new Vector3(0.25f, 0.14f, 0.045f),
            Vector3.zero,
            darkMat
        );

        CreateCylinder(
            root,
            "Camera_Lens_Black",
            new Vector3(0f, 0.44f, 0.705f),
            new Vector3(0.075f, 0.025f, 0.075f),
            new Vector3(90f, 0f, 0f),
            blackMat
        );

        CreateCylinder(
            root,
            "Camera_Glow_Cyan",
            new Vector3(0f, 0.44f, 0.728f),
            new Vector3(0.095f, 0.012f, 0.095f),
            new Vector3(90f, 0f, 0f),
            cyanLightMat
        );
    }

    private void BuildStatusBeacon(Transform root)
    {
        GameObject beacon = CreateSphere(
            root,
            "Status_Beacon",
            new Vector3(0f, 0.76f, -0.10f),
            new Vector3(0.14f, 0.14f, 0.14f),
            statusLightMat
        );

        statusRenderer = beacon.GetComponent<Renderer>();

        if (addLights)
        {
            statusLight = beacon.AddComponent<Light>();
            statusLight.type = LightType.Point;
            statusLight.color = statusColor;
            statusLight.intensity = statusLightIntensity;
            statusLight.range = lightRange;
            statusLight.shadows = LightShadows.None;
        }
    }

    private void BuildMedicalBox(Transform root)
    {
        CreateCube(
            root,
            "Medical_Box_Dark",
            new Vector3(0.42f, 0.42f, -0.08f),
            new Vector3(0.08f, 0.22f, 0.26f),
            Vector3.zero,
            darkMat
        );

        CreateCube(
            root,
            "Medical_Red_Back",
            new Vector3(0.468f, 0.42f, -0.08f),
            new Vector3(0.012f, 0.17f, 0.17f),
            Vector3.zero,
            redMat
        );

        CreateCube(
            root,
            "Medical_Cross_V",
            new Vector3(0.477f, 0.42f, -0.08f),
            new Vector3(0.014f, 0.115f, 0.034f),
            Vector3.zero,
            whiteMat
        );

        CreateCube(
            root,
            "Medical_Cross_H",
            new Vector3(0.478f, 0.42f, -0.08f),
            new Vector3(0.014f, 0.034f, 0.115f),
            Vector3.zero,
            whiteMat
        );
    }

    private void BuildAntenna(Transform root)
    {
        CreateCylinder(
            root,
            "Antenna",
            new Vector3(0.23f, 0.78f, -0.36f),
            new Vector3(0.018f, 0.14f, 0.018f),
            Vector3.zero,
            darkMat
        );

        CreateSphere(
            root,
            "Antenna_Tip",
            new Vector3(0.23f, 0.94f, -0.36f),
            new Vector3(0.045f, 0.045f, 0.045f),
            redMat
        );
    }

    private void BuildSideRails(Transform root)
    {
        CreateCube(
            root,
            "Left_Side_Rail",
            new Vector3(-0.40f, 0.45f, 0f),
            new Vector3(0.045f, 0.08f, 0.70f),
            Vector3.zero,
            metalMat
        );

        CreateCube(
            root,
            "Right_Side_Rail",
            new Vector3(0.40f, 0.45f, 0f),
            new Vector3(0.045f, 0.08f, 0.70f),
            Vector3.zero,
            metalMat
        );
    }

    private void BuildCompactLegs(Transform root)
    {
        float x = 0.37f;
        float z = 0.32f;

        BuildLeg(root, "Front_Left", -x, z);
        BuildLeg(root, "Front_Right", x, z);
        BuildLeg(root, "Back_Left", -x, -z);
        BuildLeg(root, "Back_Right", x, -z);
    }

    private void BuildLeg(Transform root, string name, float x, float z)
    {
        CreateCube(
            root,
            name + "_Upper_Leg",
            new Vector3(x, 0.27f, z),
            new Vector3(0.075f, 0.22f, 0.075f),
            new Vector3(0f, 0f, 8f * Mathf.Sign(x)),
            metalMat
        );

        CreateCube(
            root,
            name + "_Lower_Leg",
            new Vector3(x, 0.13f, z + 0.02f),
            new Vector3(0.065f, 0.19f, 0.065f),
            new Vector3(0f, 0f, -6f * Mathf.Sign(x)),
            lightMetalMat
        );

        CreateCube(
            root,
            name + "_Foot",
            new Vector3(x, 0.025f, z + 0.05f),
            new Vector3(0.18f, 0.055f, 0.24f),
            Vector3.zero,
            blackMat
        );
    }

    private void BuildRescueStripes(Transform root)
    {
        CreateCube(
            root,
            "White_Stripe_1",
            new Vector3(0f, 0.575f, -0.24f),
            new Vector3(0.50f, 0.018f, 0.032f),
            Vector3.zero,
            whiteMat
        );

        CreateCube(
            root,
            "Red_Stripe",
            new Vector3(0f, 0.577f, -0.19f),
            new Vector3(0.50f, 0.018f, 0.032f),
            Vector3.zero,
            redMat
        );

        CreateCube(
            root,
            "White_Stripe_2",
            new Vector3(0f, 0.579f, -0.14f),
            new Vector3(0.50f, 0.018f, 0.032f),
            Vector3.zero,
            whiteMat
        );
    }

    private void BuildLights(Transform root)
    {
        if (!addLights)
            return;

        AddPointLight(
            root,
            "CameraLight",
            new Vector3(0f, 0.45f, 0.80f),
            sensorColor,
            sensorLightIntensity,
            1.55f
        );

        AddPointLight(
            root,
            "SmallRedBeaconA",
            new Vector3(-0.23f, 0.72f, 0.30f),
            medicalRed,
            0.28f,
            0.9f
        );

        AddPointLight(
            root,
            "SmallRedBeaconB",
            new Vector3(0.23f, 0.72f, -0.30f),
            medicalRed,
            0.28f,
            0.9f
        );
    }

    public void SetStatusColor(Color color)
    {
        statusColor = color;

        if (statusLightMat != null)
        {
            SetMaterialColor(statusLightMat, color);

            if (statusLightMat.HasProperty("_EmissionColor"))
            {
                statusLightMat.EnableKeyword("_EMISSION");
                statusLightMat.SetColor("_EmissionColor", color * 1.8f);
            }
        }

        if (statusRenderer != null)
        {
            statusRenderer.sharedMaterial = statusLightMat;
        }

        if (statusLight != null)
        {
            statusLight.color = color;
        }
    }

    private void CreateMaterials()
    {
        bodyMat = MakeMat(bodyColor, 0f, 0.25f, 0.42f);
        yellowMat = MakeMat(rescueYellow, 0f, 0.12f, 0.35f);
        darkMat = MakeMat(darkColor, 0f, 0.15f, 0.35f);
        metalMat = MakeMat(metalColor, 0f, 0.35f, 0.50f);
        lightMetalMat = MakeMat(lightMetalColor, 0f, 0.25f, 0.45f);
        blackMat = MakeMat(new Color(0.03f, 0.03f, 0.035f), 0f, 0.10f, 0.30f);
        whiteMat = MakeMat(whiteColor, 0f, 0.05f, 0.25f);
        redMat = MakeMat(medicalRed, 1.0f, 0.05f, 0.45f);
        cyanLightMat = MakeMat(sensorColor, 1.25f, 0.05f, 0.65f);
        statusLightMat = MakeMat(statusColor, 1.8f, 0.05f, 0.65f);
    }

    private Material MakeMat(Color color, float emission, float metallic, float smoothness)
    {
        Shader shader = Shader.Find("Universal Render Pipeline/Lit");

        if (shader == null)
            shader = Shader.Find("Standard");

        Material mat = new Material(shader);

        SetMaterialColor(mat, color);

        if (mat.HasProperty("_Metallic"))
            mat.SetFloat("_Metallic", metallic);

        if (mat.HasProperty("_Smoothness"))
            mat.SetFloat("_Smoothness", smoothness);

        if (mat.HasProperty("_Glossiness"))
            mat.SetFloat("_Glossiness", smoothness);

        if (emission > 0f)
        {
            mat.EnableKeyword("_EMISSION");

            if (mat.HasProperty("_EmissionColor"))
                mat.SetColor("_EmissionColor", color * emission);
        }

        mat.color = color;

        return mat;
    }

    private void SetMaterialColor(Material mat, Color color)
    {
        if (mat == null)
            return;

        if (mat.HasProperty("_BaseColor"))
            mat.SetColor("_BaseColor", color);

        if (mat.HasProperty("_Color"))
            mat.SetColor("_Color", color);

        mat.color = color;
    }

    private GameObject CreateCube(
        Transform parent,
        string name,
        Vector3 localPos,
        Vector3 localScale,
        Vector3 localEuler,
        Material mat
    )
    {
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);

        SetupPart(
            go,
            parent,
            name,
            localPos,
            localScale,
            localEuler,
            mat
        );

        return go;
    }

    private GameObject CreateCylinder(
        Transform parent,
        string name,
        Vector3 localPos,
        Vector3 localScale,
        Vector3 localEuler,
        Material mat
    )
    {
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);

        SetupPart(
            go,
            parent,
            name,
            localPos,
            localScale,
            localEuler,
            mat
        );

        return go;
    }

    private GameObject CreateSphere(
        Transform parent,
        string name,
        Vector3 localPos,
        Vector3 localScale,
        Material mat
    )
    {
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Sphere);

        SetupPart(
            go,
            parent,
            name,
            localPos,
            localScale,
            Vector3.zero,
            mat
        );

        return go;
    }

    private void SetupPart(
        GameObject go,
        Transform parent,
        string name,
        Vector3 localPos,
        Vector3 localScale,
        Vector3 localEuler,
        Material mat
    )
    {
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPos;
        go.transform.localScale = localScale;
        go.transform.localRotation = Quaternion.Euler(localEuler);

        Renderer r = go.GetComponent<Renderer>();

        if (r != null)
        {
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.On;
            r.receiveShadows = true;
        }

        Collider c = go.GetComponent<Collider>();

        if (c != null)
        {
            SafeDestroy(c);
        }
    }

    private void AddPointLight(
        Transform parent,
        string name,
        Vector3 localPos,
        Color color,
        float intensity,
        float range
    )
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPos;

        Light l = go.AddComponent<Light>();
        l.type = LightType.Point;
        l.color = color;
        l.intensity = intensity;
        l.range = range;
        l.shadows = LightShadows.None;
    }

    private void SafeDestroy(Object obj)
    {
        if (obj == null)
            return;

        if (Application.isPlaying)
            Destroy(obj);
        else
            DestroyImmediate(obj);
    }
}