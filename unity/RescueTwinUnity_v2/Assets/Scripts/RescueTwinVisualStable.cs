using System.Collections;
using UnityEngine;
using UnityEngine.Rendering;

public class RescueRobotVisualStable : MonoBehaviour
{
    [Header("Referencia")]
    public Transform targetRobot;
    public float startDelay = 0.8f;

    [Header("Ajustes")]
    public Vector3 visualOffset = new Vector3(0f, 0.02f, 0f);
    public Vector3 visualRotation = new Vector3(0f, 0f, 0f);
    public float visualScale = 1.15f;

    [Header("Ocultar original")]
    public bool forceHideOriginalEveryFrame = true;

    [Header("Patas originales")]
    public float legVisibilityHeight = 0.32f;
    public float footHeight = 0.08f;
    public float maxVisibleLegPartSize = 0.55f;

    private Material yellowMat;
    private Material darkMat;
    private Material grayMat;
    private Material lightGrayMat;
    private Material redLightMat;
    private Material cyanLightMat;
    private Material blackMat;
    private Material whiteMat;

    private Transform visualRoot;

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
            targetRobot = FindGreenDogRobot();
        }

        if (targetRobot == null)
        {
            Debug.LogWarning("RescueRobotVisualStable: no encontré el perro. Arrastrá manualmente el objeto Robot al campo Target Robot.");
            return;
        }

        CreateMaterials();
        RemoveOldVisual();
        HideOriginalVisuals();
        BuildNewVisual();
    }

    private Transform FindGreenDogRobot()
    {
        Renderer[] renderers = FindObjectsOfType<Renderer>(true);

        foreach (Renderer r in renderers)
        {
            if (r == null || r.sharedMaterial == null)
                continue;

            string objectName = r.gameObject.name.ToLower();

            if (
                objectName.Contains("grid") ||
                objectName.Contains("route") ||
                objectName.Contains("path") ||
                objectName.Contains("trail") ||
                objectName.Contains("floor") ||
                objectName.Contains("ground") ||
                objectName.Contains("danger") ||
                objectName.Contains("risk") ||
                objectName.Contains("victim")
            )
            {
                continue;
            }

            Color c = r.sharedMaterial.color;

            if (c.g > 0.65f && c.r < 0.45f && c.b < 0.45f)
            {
                return r.transform.root;
            }
        }

        GameObject direct = GameObject.Find("Robot");

        if (direct != null)
            return direct.transform;

        GameObject[] all = FindObjectsOfType<GameObject>(true);

        foreach (GameObject go in all)
        {
            string n = go.name.ToLower();

            if (
                n.Contains("dog") ||
                n.Contains("perro") ||
                n.Contains("searchdog") ||
                n.Contains("quadruped") ||
                n.Contains("robot")
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
        Transform oldA = targetRobot.Find("__RescueRobotVisualStable__");

        if (oldA != null)
        {
            SafeDestroy(oldA.gameObject);
        }

        Transform oldB = targetRobot.Find("__RescueRobotVisual__");

        if (oldB != null)
        {
            SafeDestroy(oldB.gameObject);
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

            // No ocultar el nuevo visual amarillo.
            if (visualRoot != null && r.transform.IsChildOf(visualRoot))
                continue;

            // No tocar líneas/rutas.
            if (r.GetComponent<LineRenderer>() != null)
                continue;

            Vector3 localCenter = targetRobot.InverseTransformPoint(r.bounds.center);

            float maxSize = Mathf.Max(
                r.bounds.size.x,
                r.bounds.size.y,
                r.bounds.size.z
            );

            // Solo dejamos visibles partes bajas Y chicas.
            // Esto evita que aparezca el cuerpo/cilindro original gigante.
            bool isLowEnough = localCenter.y < legVisibilityHeight;
            bool isSmallEnough = maxSize < maxVisibleLegPartSize;

            bool isOriginalLegOrFoot = isLowEnough && isSmallEnough;

            r.enabled = isOriginalLegOrFoot;

            if (isOriginalLegOrFoot)
            {
                if (localCenter.y < footHeight)
                {
                    r.sharedMaterial = blackMat;      // pies
                }
                else
                {
                    r.sharedMaterial = lightGrayMat;  // patas
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

        // =========================
        // CUERPO PRINCIPAL
        // =========================
        CreateCube(
            root.transform,
            "Body_Main",
            new Vector3(0f, 0.42f, 0f),
            new Vector3(0.72f, 0.22f, 0.98f),
            Vector3.zero,
            yellowMat
        );

        CreateCube(
            root.transform,
            "Body_Top",
            new Vector3(0f, 0.58f, 0f),
            new Vector3(0.50f, 0.12f, 0.55f),
            Vector3.zero,
            yellowMat
        );

        // =========================
        // CABEZA / CÁMARA FRONTAL
        // =========================
        CreateCube(
            root.transform,
            "Front_Head",
            new Vector3(0f, 0.42f, 0.56f),
            new Vector3(0.46f, 0.22f, 0.20f),
            Vector3.zero,
            yellowMat
        );

        CreateCube(
            root.transform,
            "Camera_Frame",
            new Vector3(0f, 0.42f, 0.69f),
            new Vector3(0.25f, 0.16f, 0.055f),
            Vector3.zero,
            darkMat
        );

        CreateCylinder(
            root.transform,
            "Camera_Lens",
            new Vector3(0f, 0.42f, 0.735f),
            new Vector3(0.075f, 0.025f, 0.075f),
            new Vector3(90f, 0f, 0f),
            blackMat
        );

        CreateCylinder(
            root.transform,
            "Camera_Glow",
            new Vector3(0f, 0.42f, 0.755f),
            new Vector3(0.095f, 0.012f, 0.095f),
            new Vector3(90f, 0f, 0f),
            cyanLightMat
        );

        // =========================
        // LUCES ROJAS SUPERIORES
        // =========================
        CreateCube(
            root.transform,
            "Red_Light_Front",
            new Vector3(-0.25f, 0.70f, 0.34f),
            new Vector3(0.18f, 0.055f, 0.13f),
            Vector3.zero,
            redLightMat
        );

        CreateCube(
            root.transform,
            "Red_Light_Back",
            new Vector3(0.25f, 0.70f, -0.34f),
            new Vector3(0.18f, 0.055f, 0.13f),
            Vector3.zero,
            redLightMat
        );

        // =========================
        // CAJA MÉDICA LATERAL
        // =========================
        CreateCube(
            root.transform,
            "Medical_Box",
            new Vector3(0.42f, 0.39f, -0.08f),
            new Vector3(0.08f, 0.22f, 0.26f),
            Vector3.zero,
            darkMat
        );

        CreateCube(
            root.transform,
            "Medical_Red_Back",
            new Vector3(0.466f, 0.39f, -0.08f),
            new Vector3(0.012f, 0.17f, 0.17f),
            Vector3.zero,
            redLightMat
        );

        CreateCube(
            root.transform,
            "Medical_Cross_V",
            new Vector3(0.474f, 0.39f, -0.08f),
            new Vector3(0.014f, 0.12f, 0.035f),
            Vector3.zero,
            whiteMat
        );

        CreateCube(
            root.transform,
            "Medical_Cross_H",
            new Vector3(0.475f, 0.39f, -0.08f),
            new Vector3(0.014f, 0.035f, 0.12f),
            Vector3.zero,
            whiteMat
        );

        // =========================
        // ANTENA
        // =========================
        CreateCylinder(
            root.transform,
            "Antenna",
            new Vector3(0.22f, 0.86f, -0.34f),
            new Vector3(0.02f, 0.16f, 0.02f),
            Vector3.zero,
            darkMat
        );

        CreateSphere(
            root.transform,
            "Antenna_Tip",
            new Vector3(0.22f, 1.04f, -0.34f),
            new Vector3(0.06f, 0.06f, 0.06f),
            redLightMat
        );

        // =========================
        // FRANJAS DE RESCATE
        // =========================
        CreateCube(
            root.transform,
            "White_Stripe",
            new Vector3(0f, 0.305f, -0.22f),
            new Vector3(0.68f, 0.025f, 0.035f),
            Vector3.zero,
            whiteMat
        );

        CreateCube(
            root.transform,
            "Red_Stripe",
            new Vector3(0f, 0.300f, -0.17f),
            new Vector3(0.68f, 0.025f, 0.035f),
            Vector3.zero,
            redLightMat
        );

        CreateCube(
            root.transform,
            "White_Stripe_2",
            new Vector3(0f, 0.295f, -0.12f),
            new Vector3(0.68f, 0.025f, 0.035f),
            Vector3.zero,
            whiteMat
        );

        // =========================
        // LUCES REALES
        // =========================
        AddPointLight(
            root.transform,
            "CameraLight",
            new Vector3(0f, 0.43f, 0.80f),
            new Color(0.25f, 1f, 1f),
            0.65f,
            1.8f
        );

        AddPointLight(
            root.transform,
            "RedLightA",
            new Vector3(-0.25f, 0.76f, 0.34f),
            new Color(1f, 0.1f, 0.08f),
            0.45f,
            1.3f
        );

        AddPointLight(
            root.transform,
            "RedLightB",
            new Vector3(0.25f, 0.76f, -0.34f),
            new Color(1f, 0.1f, 0.08f),
            0.45f,
            1.3f
        );
    }

    private void CreateMaterials()
    {
        yellowMat = MakeMat(new Color(0.96f, 0.72f, 0.08f), 0f);
        darkMat = MakeMat(new Color(0.12f, 0.12f, 0.13f), 0f);
        grayMat = MakeMat(new Color(0.40f, 0.42f, 0.44f), 0f);
        lightGrayMat = MakeMat(new Color(0.72f, 0.72f, 0.74f), 0f);
        blackMat = MakeMat(new Color(0.035f, 0.035f, 0.04f), 0f);
        whiteMat = MakeMat(new Color(0.94f, 0.94f, 0.92f), 0f);
        redLightMat = MakeMat(new Color(0.95f, 0.08f, 0.05f), 1.2f);
        cyanLightMat = MakeMat(new Color(0.10f, 0.95f, 1f), 1.2f);
    }

    private Material MakeMat(Color color, float emission)
    {
        Shader shader = Shader.Find("Universal Render Pipeline/Lit");

        if (shader == null)
            shader = Shader.Find("Standard");

        Material mat = new Material(shader);

        if (mat.HasProperty("_BaseColor"))
            mat.SetColor("_BaseColor", color);

        if (mat.HasProperty("_Color"))
            mat.SetColor("_Color", color);

        if (mat.HasProperty("_EmissionColor") && emission > 0f)
        {
            mat.EnableKeyword("_EMISSION");
            mat.SetColor("_EmissionColor", color * emission);
        }

        mat.color = color;

        return mat;
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