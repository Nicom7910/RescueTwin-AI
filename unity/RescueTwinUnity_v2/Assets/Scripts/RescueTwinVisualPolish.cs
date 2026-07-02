using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

public class RescueTwinVisualPolish : MonoBehaviour
{
    [Header("General")]
    public bool buildOnStart = true;
    public bool addExtraInteriorDebris = true;

    [Header("Grid")]
    public float gridSpacing = 1f;
    public float gridThickness = 0.015f;
    public Color gridColor = new Color(0f, 0.85f, 1f);

    [Header("Robot Route")]
    public Color routeColor = new Color(1f, 0.72f, 0.10f);
    public float routeWidth = 0.18f;
    public float dynamicTrailWidth = 0.22f;
    public float minTrailDistance = 0.20f;
    public float teleportResetDistance = 4.5f;

    [Header("Visual Style")]
    public Color floorColor = new Color(0.08f, 0.09f, 0.10f);
    public Color rubbleColor = new Color(0.48f, 0.46f, 0.42f);
    public Color darkRubbleColor = new Color(0.25f, 0.25f, 0.25f);
    public Color metalColor = new Color(0.28f, 0.32f, 0.36f);
    public Color dangerColor = new Color(1f, 0.08f, 0.04f);

    [Header("Entorno")]
    public float wallHeight = 1.25f;
    public float wallThickness = 0.22f;
    public float wallMargin = 0.25f;
    public Color wallColor = new Color(0.44f, 0.40f, 0.34f);

    [Header("Props")]
    public int rubbleMoundCount = 4;
    public int rocksPerMound = 14;
    public float moundRadius = 1.05f;

    [Header("Víctimas")]
    public Color victimSkinColor = new Color(0.85f, 0.68f, 0.55f);
    public Color victimClothColor = new Color(0.85f, 0.45f, 0.10f);
    public Color victimFallbackBeaconColor = new Color(0.85f, 0.20f, 0.85f);
    public float victimScale = 20.0f;

    private Transform visualsRoot;

    private Material floorMat;
    private Material gridMat;
    private Material routeMat;
    private Material dangerMat;
    private Material rubbleMat;
    private Material darkRubbleMat;
    private Material metalMat;
    private Material coneMat;
    private Material barrelMat;
    private Material robotMat;
    private Material wallMat;
    private Material stripeYellowMat;
    private Material stripeBlackMat;
    private Material victimSkinMat;
    private Material victimClothMat;

    private Transform robot;
    private LineRenderer dynamicTrail;
    private readonly List<Vector3> trailPoints = new List<Vector3>();

    private float trailY = 0.10f;

    private IEnumerator Start()
    {
        if (!buildOnStart)
            yield break;

        yield return new WaitForSeconds(0.35f);

        RebuildVisuals();
    }

    private void Update()
    {
        UpdateDynamicTrail();
    }

    [ContextMenu("Rebuild Visuals")]
    public void RebuildVisuals()
    {
        Random.InitState(42);

        CleanOldGeneratedObjects();
        PrepareMaterials();
        EnsureRoot();

        GameObject ground = GameObject.Find("Ground");

        if (ground == null)
        {
            Debug.LogWarning("RescueTwinVisualPolish: No se encontró el objeto Ground.");
            return;
        }

        Bounds groundBounds = GetObjectBounds(ground);
        trailY = groundBounds.max.y + 0.12f;

        PolishGround(ground);
        BuildThinCyanGrid(groundBounds);
        UpgradeDangerZonesToCrosses(groundBounds);
        PolishExistingRoute();
        PolishRobot();
        PolishVictims();
        StylizeGameplayObstacles();

        if (addExtraInteriorDebris)
        {
            BuildRubbleMounds(groundBounds);
            BuildInteriorEmergencyProps(groundBounds);
        }

        BuildPerimeterWalls(groundBounds);
        BuildCornerLights(groundBounds);

        PolishLighting(groundBounds);
        PolishCamera(groundBounds);
        CreateDynamicRobotTrail();

        Debug.Log("RescueTwinVisualPolish aplicado correctamente.");
    }

    private void CleanOldGeneratedObjects()
    {
        string[] names =
        {
            "__VisualPolishRoot__",
            "Generated_Tactical_Rescue_Visuals",
            "Generated_Rescue_Visuals",
            "Robot_Trail_Cyan",
            "Robot_Trail_Amber",
            "RobotTrail"
        };

        foreach (string n in names)
        {
            GameObject obj = GameObject.Find(n);

            if (obj != null)
            {
                SafeDestroy(obj);
            }
        }

        GameObject[] all = FindObjectsOfType<GameObject>(true);

        foreach (GameObject obj in all)
        {
            if (obj.name.StartsWith("Label_"))
            {
                SafeDestroy(obj);
            }
        }

        ClearObstacleDetailRoots();
    }

    private void EnsureRoot()
    {
        GameObject root = new GameObject("__VisualPolishRoot__");
        root.transform.SetParent(transform, false);
        visualsRoot = root.transform;
    }

    private void PrepareMaterials()
    {
        floorMat = CreateMaterial(
            "Mat_Floor_Dark_Rescue",
            floorColor,
            0f,
            true
        );

        gridMat = CreateMaterial(
            "Mat_Thin_Cyan_Grid",
            gridColor,
            1.45f,
            false
        );

        routeMat = CreateMaterial(
            "Mat_Robot_Route_Amber",
            routeColor,
            2.8f,
            false
        );

        dangerMat = CreateMaterial(
            "Mat_Danger_Red_Glow",
            dangerColor,
            2.8f,
            false
        );

        rubbleMat = CreateMaterial(
            "Mat_Rubble_Concrete",
            rubbleColor,
            0f,
            true
        );

        darkRubbleMat = CreateMaterial(
            "Mat_Rubble_Dark",
            darkRubbleColor,
            0f,
            true
        );

        metalMat = CreateMaterial(
            "Mat_Damaged_Metal",
            metalColor,
            0f,
            true
        );

        coneMat = CreateMaterial(
            "Mat_Emergency_Cone",
            new Color(1f, 0.45f, 0.08f),
            0.15f,
            true
        );

        barrelMat = CreateMaterial(
            "Mat_Barrel",
            new Color(0.70f, 0.30f, 0.06f),
            0.1f,
            true
        );

        robotMat = CreateMaterial(
            "Mat_Robot_Dark",
            new Color(0.05f, 0.06f, 0.10f),
            0f,
            true
        );

        wallMat = CreateMaterial(
            "Mat_Perimeter_Wall",
            wallColor,
            0f,
            true
        );

        stripeYellowMat = CreateMaterial(
            "Mat_Stripe_Yellow",
            new Color(1f, 0.82f, 0.05f),
            0.4f,
            true
        );

        stripeBlackMat = CreateMaterial(
            "Mat_Stripe_Black",
            new Color(0.05f, 0.05f, 0.05f),
            0f,
            true
        );

        victimSkinMat = CreateMaterial(
            "Mat_Victim_Skin",
            victimSkinColor,
            0f,
            true
        );

        victimClothMat = CreateMaterial(
            "Mat_Victim_Cloth",
            victimClothColor,
            0f,
            true
        );
    }

    private void PolishGround(GameObject ground)
    {
        Renderer r = ground.GetComponent<Renderer>();

        if (r != null)
        {
            r.sharedMaterial = floorMat;
            r.shadowCastingMode = ShadowCastingMode.On;
            r.receiveShadows = true;
        }
    }

    private void BuildThinCyanGrid(Bounds bounds)
    {
        float y = bounds.max.y + 0.035f;

        float minX = Mathf.Ceil(bounds.min.x);
        float maxX = Mathf.Floor(bounds.max.x);
        float minZ = Mathf.Ceil(bounds.min.z);
        float maxZ = Mathf.Floor(bounds.max.z);

        for (float x = minX; x <= maxX; x += gridSpacing)
        {
            CreateGridLine(
                new Vector3(x, y, bounds.min.z),
                new Vector3(x, y, bounds.max.z)
            );
        }

        for (float z = minZ; z <= maxZ; z += gridSpacing)
        {
            CreateGridLine(
                new Vector3(bounds.min.x, y, z),
                new Vector3(bounds.max.x, y, z)
            );
        }
    }

    private void CreateGridLine(Vector3 start, Vector3 end)
    {
        GameObject obj = new GameObject("Thin_Cyan_Grid_Line");
        obj.transform.SetParent(visualsRoot, false);

        LineRenderer line = obj.AddComponent<LineRenderer>();
        line.useWorldSpace = true;
        line.positionCount = 2;
        line.SetPosition(0, start);
        line.SetPosition(1, end);

        line.startWidth = gridThickness;
        line.endWidth = gridThickness;

        line.material = gridMat;
        line.startColor = new Color(gridColor.r, gridColor.g, gridColor.b, 0.60f);
        line.endColor = new Color(gridColor.r, gridColor.g, gridColor.b, 0.60f);

        line.numCornerVertices = 2;
        line.numCapVertices = 2;
        line.shadowCastingMode = ShadowCastingMode.Off;
        line.receiveShadows = false;
    }

    private void UpgradeDangerZonesToCrosses(Bounds bounds)
    {
        Renderer[] renderers = FindObjectsOfType<Renderer>(true);

        foreach (Renderer r in renderers)
        {
            if (r == null || r.transform.IsChildOf(visualsRoot))
                continue;

            string n = r.gameObject.name.ToLower();

            bool isDanger =
                n.Contains("risk") ||
                n.Contains("danger") ||
                n.Contains("alto") ||
                n.Contains("hazard") ||
                n.Contains("red");

            if (!isDanger)
                continue;

            r.sharedMaterial = dangerMat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.enabled = false;

            Vector3 pos = r.bounds.center;
            pos.y = bounds.max.y + 0.03f;

            BuildDangerCross(pos);
        }
    }

    private void BuildDangerCross(Vector3 position)
    {
        GameObject parent = new GameObject("Danger_Zone_Mark");
        parent.transform.SetParent(visualsRoot, false);
        parent.transform.position = position;

        float squareSize = gridSpacing * 0.80f;

        GameObject square = GameObject.CreatePrimitive(PrimitiveType.Cube);
        square.name = "Danger_Square";
        square.transform.SetParent(parent.transform, false);
        square.transform.localPosition = Vector3.zero;
        square.transform.localRotation = Quaternion.identity;
        square.transform.localScale = new Vector3(squareSize, 0.01f, squareSize);
        ApplyFlatMaterial(square, dangerMat);
        RemoveCollider(square);
    }

    private void PolishExistingRoute()
    {
        LineRenderer[] lines = FindObjectsOfType<LineRenderer>(true);

        foreach (LineRenderer lr in lines)
        {
            if (lr == null || lr.transform.IsChildOf(visualsRoot))
                continue;

            string n = lr.gameObject.name.ToLower();

            bool looksLikeRoute =
                n.Contains("route") ||
                n.Contains("path") ||
                n.Contains("trajectory") ||
                n.Contains("recorrido") ||
                n.Contains("trail");

            if (!looksLikeRoute)
                continue;

            ApplyRouteStyle(lr);
        }
    }

    private void ApplyRouteStyle(LineRenderer lr)
    {
        lr.material = routeMat;
        lr.startColor = routeColor;
        lr.endColor = routeColor;
        lr.startWidth = routeWidth;
        lr.endWidth = routeWidth;
        lr.numCornerVertices = 8;
        lr.numCapVertices = 8;
        lr.shadowCastingMode = ShadowCastingMode.Off;
        lr.receiveShadows = false;
        lr.alignment = LineAlignment.View;
    }

    private void PolishRobot()
    {
        robot = FindRobot();

        if (robot == null)
        {
            Debug.LogWarning("RescueTwinVisualPolish: no se encontró el perro robot.");
            return;
        }

        ClearRobotVisualUpgrade(robot);
        BuildRobotVisualUpgrade(robot);

        CreatePointLight(
            "Robot_Sensor_Amber_Light",
            robot.position + new Vector3(0f, 0.8f, 0.25f),
            routeColor,
            1.1f,
            3.5f
        );
    }

    private void ClearRobotVisualUpgrade(Transform robotTransform)
    {
        Transform old = robotTransform.Find("__RobotVisualUpgrade__");

        if (old != null)
        {
            SafeDestroy(old.gameObject);
        }
    }

    private void BuildRobotVisualUpgrade(Transform robotTransform)
    {
        GameObject upgradeRoot = new GameObject("__RobotVisualUpgrade__");
        upgradeRoot.transform.SetParent(robotTransform, false);
        upgradeRoot.transform.localPosition = Vector3.zero;
        upgradeRoot.transform.localRotation = Quaternion.identity;
        upgradeRoot.transform.localScale = Vector3.one;

        // Sombra/base suave debajo del perro.
        CreateRobotLocalPart(
            PrimitiveType.Cylinder,
            "Robot_Shadow_Base",
            new Vector3(0f, 0.035f, 0f),
            new Vector3(0.48f, 0.025f, 0.72f),
            Vector3.zero,
            darkRubbleMat,
            upgradeRoot.transform
        );

        // Módulo superior tipo sensor/caja tecnológica.
        CreateRobotLocalPart(
            PrimitiveType.Cube,
            "Robot_Top_Sensor_Box",
            new Vector3(0f, 0.58f, 0f),
            new Vector3(0.42f, 0.16f, 0.36f),
            Vector3.zero,
            metalMat,
            upgradeRoot.transform
        );

        // Cámara frontal.
        CreateRobotLocalPart(
            PrimitiveType.Cylinder,
            "Robot_Front_Camera_Lens",
            new Vector3(0f, 0.60f, 0.38f),
            new Vector3(0.09f, 0.035f, 0.09f),
            new Vector3(90f, 0f, 0f),
            darkRubbleMat,
            upgradeRoot.transform
        );

        // Aro/luz del sensor.
        CreateRobotLocalPart(
            PrimitiveType.Cylinder,
            "Robot_Front_Camera_Glow",
            new Vector3(0f, 0.60f, 0.405f),
            new Vector3(0.12f, 0.018f, 0.12f),
            new Vector3(90f, 0f, 0f),
            routeMat,
            upgradeRoot.transform
        );

        // Antena.
        CreateRobotLocalPart(
            PrimitiveType.Cylinder,
            "Robot_Antenna",
            new Vector3(0.18f, 0.82f, -0.10f),
            new Vector3(0.025f, 0.22f, 0.025f),
            Vector3.zero,
            metalMat,
            upgradeRoot.transform
        );

        CreateRobotLocalPart(
            PrimitiveType.Sphere,
            "Robot_Antenna_Tip",
            new Vector3(0.18f, 1.05f, -0.10f),
            new Vector3(0.075f, 0.075f, 0.075f),
            Vector3.zero,
            routeMat,
            upgradeRoot.transform
        );

        // Panel lateral izquierdo.
        CreateRobotLocalPart(
            PrimitiveType.Cube,
            "Robot_Left_Tech_Panel",
            new Vector3(-0.36f, 0.43f, 0.02f),
            new Vector3(0.045f, 0.18f, 0.34f),
            Vector3.zero,
            metalMat,
            upgradeRoot.transform
        );

        // Panel lateral derecho.
        CreateRobotLocalPart(
            PrimitiveType.Cube,
            "Robot_Right_Tech_Panel",
            new Vector3(0.36f, 0.43f, 0.02f),
            new Vector3(0.045f, 0.18f, 0.34f),
            Vector3.zero,
            metalMat,
            upgradeRoot.transform
        );

        // Luces chicas laterales.
        CreateRobotLocalPart(
            PrimitiveType.Sphere,
            "Robot_Left_Status_Light",
            new Vector3(-0.39f, 0.50f, 0.24f),
            new Vector3(0.055f, 0.055f, 0.055f),
            Vector3.zero,
            routeMat,
            upgradeRoot.transform
        );

        CreateRobotLocalPart(
            PrimitiveType.Sphere,
            "Robot_Right_Status_Light",
            new Vector3(0.39f, 0.50f, 0.24f),
            new Vector3(0.055f, 0.055f, 0.055f),
            Vector3.zero,
            routeMat,
            upgradeRoot.transform
        );

        // Luz real del sensor.
        GameObject sensorLightObject = new GameObject("Robot_Local_Sensor_Light");
        sensorLightObject.transform.SetParent(upgradeRoot.transform, false);
        sensorLightObject.transform.localPosition = new Vector3(0f, 0.65f, 0.55f);

        Light sensorLight = sensorLightObject.AddComponent<Light>();
        sensorLight.type = LightType.Point;
        sensorLight.color = routeColor;
        sensorLight.intensity = 0.9f;
        sensorLight.range = 2.5f;
        sensorLight.shadows = LightShadows.None;
    }

    private GameObject CreateRobotLocalPart(
        PrimitiveType type,
        string name,
        Vector3 localPosition,
        Vector3 localScale,
        Vector3 localEuler,
        Material material,
        Transform parent
    )
    {
        GameObject part = GameObject.CreatePrimitive(type);
        part.name = name;

        part.transform.SetParent(parent, false);
        part.transform.localPosition = localPosition;
        part.transform.localScale = localScale;
        part.transform.localRotation = Quaternion.Euler(localEuler);

        Renderer renderer = part.GetComponent<Renderer>();

        if (renderer != null)
        {
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = ShadowCastingMode.On;
            renderer.receiveShadows = true;
        }

        Collider collider = part.GetComponent<Collider>();

        if (collider != null)
        {
            SafeDestroy(collider);
        }

        return part;
    }
    
    private void PolishVictims()
    {
        Renderer[] renderers = FindObjectsOfType<Renderer>(true);
        HashSet<Transform> processed = new HashSet<Transform>();

        foreach (Renderer r in renderers)
        {
            if (r == null)
                continue;

            if (visualsRoot != null && r.transform.IsChildOf(visualsRoot))
                continue;

            string n = r.gameObject.name.ToLower();

            if (!n.Contains("victim") && !n.Contains("victima"))
                continue;

            if (processed.Contains(r.transform))
                continue;

            processed.Add(r.transform);
            BuildVictimFigure(r.transform, r);
        }
    }

    private void BuildVictimFigure(Transform victimRoot, Renderer originalRenderer)
    {
        Color beaconColor = victimFallbackBeaconColor;

        if (originalRenderer != null && originalRenderer.sharedMaterial != null)
        {
            beaconColor = originalRenderer.sharedMaterial.color;
        }

        if (originalRenderer != null)
        {
            originalRenderer.enabled = false;
        }

        Transform old = victimRoot.Find("__VictimFigure__");

        if (old != null)
        {
            SafeDestroy(old.gameObject);
        }

        GameObject figureRoot = new GameObject("__VictimFigure__");
        figureRoot.transform.SetParent(victimRoot, false);
        figureRoot.transform.localPosition = Vector3.zero;
        figureRoot.transform.localRotation = Quaternion.identity;
        figureRoot.transform.localScale = Vector3.one * victimScale;

        GameObject torso = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        torso.name = "Victim_Torso";
        torso.transform.SetParent(figureRoot.transform, false);
        torso.transform.localPosition = new Vector3(0f, 0.30f, 0f);
        torso.transform.localScale = new Vector3(0.22f, 0.22f, 0.22f);
        ApplyMaterial(torso, victimClothMat);
        RemoveCollider(torso);

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "Victim_Head";
        head.transform.SetParent(figureRoot.transform, false);
        head.transform.localPosition = new Vector3(0f, 0.58f, 0f);
        head.transform.localScale = Vector3.one * 0.19f;
        ApplyMaterial(head, victimSkinMat);
        RemoveCollider(head);

        BuildVictimArm(figureRoot.transform, new Vector3(-0.15f, 0.46f, 0f), -30f);
        BuildVictimArm(figureRoot.transform, new Vector3(0.15f, 0.46f, 0f), 30f);

        GameObject beacon = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        beacon.name = "Victim_Signal_Beacon";
        beacon.transform.SetParent(figureRoot.transform, false);
        beacon.transform.localPosition = new Vector3(0f, 0.88f, 0f);
        beacon.transform.localScale = Vector3.one * 0.085f;

        Material beaconMat = CreateMaterial(
            "Mat_Victim_Beacon_" + victimRoot.GetInstanceID(),
            beaconColor,
            2.2f,
            false
        );

        ApplyMaterial(beacon, beaconMat);
        RemoveCollider(beacon);

        Light l = beacon.AddComponent<Light>();
        l.type = LightType.Point;
        l.color = beaconColor;
        l.intensity = 0.9f;
        l.range = 2.0f;
        l.shadows = LightShadows.None;
    }

    private void BuildVictimArm(Transform parent, Vector3 shoulderLocalPos, float zTilt)
    {
        GameObject arm = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        arm.name = "Victim_Arm";
        arm.transform.SetParent(parent, false);
        arm.transform.localPosition = shoulderLocalPos;
        arm.transform.localRotation = Quaternion.Euler(0f, 0f, zTilt);
        arm.transform.localScale = new Vector3(0.055f, 0.13f, 0.055f);
        ApplyMaterial(arm, victimSkinMat);
        RemoveCollider(arm);
    }

    private void StylizeGameplayObstacles()
    {
        Renderer[] renderers = FindObjectsOfType<Renderer>(true);

        foreach (Renderer r in renderers)
        {
            if (r == null)
                continue;

            if (visualsRoot != null && r.transform.IsChildOf(visualsRoot))
                continue;

            GameObject obj = r.gameObject;
            string n = obj.name.ToLower();

            if (ShouldSkipObjectForObstacleStyle(n, obj))
                continue;

            Bounds b = r.bounds;

            if (b.size.x > 3.5f || b.size.z > 3.5f || b.size.y > 3.5f)
                continue;

            r.sharedMaterial =
                Random.value > 0.45f
                    ? rubbleMat
                    : darkRubbleMat;

            AddDetailChunksAroundObstacle(obj.transform);
        }
    }

    private bool ShouldSkipObjectForObstacleStyle(string name, GameObject obj)
    {
        if (name.Contains("ground")) return true;
        if (name.Contains("floor")) return true;
        if (name.Contains("wall")) return true;
        if (name.Contains("grid")) return true;
        if (name.Contains("hazard")) return true;
        if (name.Contains("risk")) return true;
        if (name.Contains("danger")) return true;
        if (name.Contains("red")) return true;
        if (name.Contains("robot")) return true;
        if (name.Contains("dog")) return true;
        if (name.Contains("victim")) return true;
        if (name.Contains("marker")) return true;
        if (name.Contains("camera")) return true;
        if (name.Contains("light")) return true;
        if (name.Contains("route")) return true;
        if (name.Contains("path")) return true;
        if (name.Contains("trajectory")) return true;
        if (name.Contains("base")) return true;
        if (name.Contains("ui")) return true;
        if (name.Contains("canvas")) return true;

        Renderer renderer = obj.GetComponent<Renderer>();

        if (renderer == null)
            return true;

        return false;
    }

    private void AddDetailChunksAroundObstacle(Transform obstacle)
    {
        Transform old = obstacle.Find("__ObstacleDetailChunks__");

        if (old != null)
        {
            SafeDestroy(old.gameObject);
        }

        GameObject detailRoot = new GameObject("__ObstacleDetailChunks__");
        detailRoot.transform.SetParent(obstacle, false);
        detailRoot.transform.localPosition = Vector3.zero;
        detailRoot.transform.localRotation = Quaternion.identity;
        detailRoot.transform.localScale = Vector3.one;

        int pieces = Random.Range(4, 8);

        for (int i = 0; i < pieces; i++)
        {
            GameObject piece = GameObject.CreatePrimitive(PrimitiveType.Cube);
            piece.name = "Small_Rubble_Detail";
            piece.transform.SetParent(detailRoot.transform, false);

            piece.transform.localPosition = new Vector3(
                Random.Range(-0.60f, 0.60f),
                Random.Range(-0.30f, 0.18f),
                Random.Range(-0.60f, 0.60f)
            );

            piece.transform.localRotation = Random.rotation;

            float baseScale = Random.Range(0.08f, 0.26f);

            piece.transform.localScale = new Vector3(
                baseScale * Random.Range(0.7f, 1.3f),
                baseScale * Random.Range(0.5f, 1.0f),
                baseScale * Random.Range(0.7f, 1.3f)
            );

            Renderer pr = piece.GetComponent<Renderer>();

            if (pr != null)
            {
                float roll = Random.value;

                pr.sharedMaterial =
                    roll > 0.80f ? metalMat :
                    roll > 0.40f ? rubbleMat :
                    darkRubbleMat;
            }

            RemoveCollider(piece);
        }
    }

    private void BuildRubbleMounds(Bounds bounds)
    {
        for (int m = 0; m < rubbleMoundCount; m++)
        {
            Vector3 center = new Vector3(
                Random.Range(bounds.min.x + 1.5f, bounds.max.x - 1.5f),
                bounds.max.y,
                Random.Range(bounds.min.z + 1.5f, bounds.max.z - 1.5f)
            );

            BuildOneMound(center);
        }

        CreateVisualCube(
            "Metal_Container_Inside",
            bounds.center + new Vector3(bounds.extents.x * 0.35f, bounds.max.y + 0.28f, -bounds.extents.z * 0.35f),
            new Vector3(1.1f, 0.55f, 0.70f),
            Vector3.zero,
            metalMat
        );
    }

    private void BuildOneMound(Vector3 center)
    {
        GameObject moundRoot = new GameObject("Rubble_Mound");
        moundRoot.transform.SetParent(visualsRoot, false);
        moundRoot.transform.position = center;

        for (int i = 0; i < rocksPerMound; i++)
        {
            float t = (float)i / rocksPerMound;
            float radius = moundRadius * (1f - t * 0.6f) * Random.Range(0.5f, 1f);
            float angle = Random.Range(0f, Mathf.PI * 2f);

            Vector3 localPos = new Vector3(
                Mathf.Cos(angle) * radius,
                Random.Range(0.05f, 0.05f + (1f - t) * 0.55f),
                Mathf.Sin(angle) * radius
            );

            GameObject rock = GameObject.CreatePrimitive(PrimitiveType.Cube);
            rock.name = "Rock";
            rock.transform.SetParent(moundRoot.transform, false);
            rock.transform.localPosition = localPos;
            rock.transform.localRotation = Random.rotation;

            float scale = Random.Range(0.18f, 0.42f) * (1f - t * 0.35f);
            rock.transform.localScale = new Vector3(
                scale,
                scale * Random.Range(0.7f, 1.1f),
                scale
            );

            ApplyMaterial(rock, Random.value > 0.5f ? rubbleMat : darkRubbleMat);
            RemoveCollider(rock);
        }
    }

    private void BuildPerimeterWalls(Bounds bounds)
    {
        float x1 = bounds.min.x - wallMargin;
        float x2 = bounds.max.x + wallMargin;
        float z1 = bounds.min.z - wallMargin;
        float z2 = bounds.max.z + wallMargin;
        float y = bounds.max.y;

        BuildWallSegment(
            new Vector3((x1 + x2) * 0.5f, y, z2),
            new Vector3(x2 - x1, wallHeight, wallThickness)
        );

        BuildWallSegment(
            new Vector3(x1, y, (z1 + z2) * 0.5f),
            new Vector3(wallThickness, wallHeight, z2 - z1)
        );

        BuildWallSegment(
            new Vector3(x2, y, (z1 + z2) * 0.5f),
            new Vector3(wallThickness, wallHeight, z2 - z1)
        );

        BuildLowFrontBarrier(
            new Vector3((x1 + x2) * 0.5f, y, z1),
            new Vector3(x2 - x1, 0.22f, wallThickness)
        );
    }

    private void BuildWallSegment(Vector3 center, Vector3 size)
    {
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = "Perimeter_Wall";
        go.transform.SetParent(visualsRoot, false);
        go.transform.position = center + Vector3.up * (size.y * 0.5f);
        go.transform.localScale = size;
        ApplyMaterial(go, wallMat);
        RemoveCollider(go);
    }

    private void BuildLowFrontBarrier(Vector3 center, Vector3 size)
    {
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = "Low_Front_Barrier";
        go.transform.SetParent(visualsRoot, false);
        go.transform.position = center + Vector3.up * (size.y * 0.5f);
        go.transform.localScale = size;
        ApplyMaterial(go, wallMat);
        RemoveCollider(go);
    }

    private void BuildCornerLights(Bounds bounds)
    {
        Vector3[] corners =
        {
            new Vector3(bounds.min.x - 0.2f, bounds.max.y, bounds.min.z - 0.2f),
            new Vector3(bounds.max.x + 0.2f, bounds.max.y, bounds.min.z - 0.2f),
            new Vector3(bounds.min.x - 0.2f, bounds.max.y, bounds.max.z + 0.2f),
            new Vector3(bounds.max.x + 0.2f, bounds.max.y, bounds.max.z + 0.2f)
        };

        foreach (Vector3 c in corners)
        {
            CreatePointLight(
                "Corner_Work_Light",
                c + Vector3.up * 2.6f,
                new Color(1f, 0.92f, 0.75f),
                1.4f,
                7f
            );
        }
    }

    private void BuildInteriorEmergencyProps(Bounds bounds)
    {
        Vector3 p1 = bounds.center + new Vector3(-bounds.extents.x * 0.55f, 0f, bounds.extents.z * 0.65f);
        Vector3 p2 = bounds.center + new Vector3(bounds.extents.x * 0.55f, 0f, -bounds.extents.z * 0.65f);
        Vector3 p3 = bounds.center + new Vector3(bounds.extents.x * 0.40f, 0f, bounds.extents.z * 0.45f);

        CreateCone(p1);
        CreateCone(p1 + new Vector3(0.35f, 0f, 0f));
        CreateCone(p1 + new Vector3(0.70f, 0f, 0f));

        CreateCone(p2);
        CreateCone(p2 + new Vector3(-0.35f, 0f, 0.15f));

        CreateBarrel(p3);
        CreateSmallBarrier(bounds.center + new Vector3(bounds.extents.x * 0.55f, 0f, bounds.extents.z * 0.20f), 90f);
    }

    private void CreateCone(Vector3 position)
    {
        position.y = trailY;

        CreateVisualPrimitive(
            PrimitiveType.Cylinder,
            "Cone_Base",
            position + new Vector3(0f, 0.025f, 0f),
            new Vector3(0.18f, 0.025f, 0.18f),
            Vector3.zero,
            metalMat
        );

        CreateVisualPrimitive(
            PrimitiveType.Cylinder,
            "Cone_Body",
            position + new Vector3(0f, 0.18f, 0f),
            new Vector3(0.10f, 0.18f, 0.10f),
            Vector3.zero,
            coneMat
        );
    }

    private void CreateBarrel(Vector3 position)
    {
        position.y = trailY;

        CreateVisualPrimitive(
            PrimitiveType.Cylinder,
            "Emergency_Barrel",
            position + new Vector3(0f, 0.28f, 0f),
            new Vector3(0.23f, 0.28f, 0.23f),
            Vector3.zero,
            barrelMat
        );
    }

    private void CreateSmallBarrier(Vector3 position, float yRotation)
    {
        position.y = trailY + 0.20f;

        GameObject parent = new GameObject("Interior_Barrier");
        parent.transform.SetParent(visualsRoot, false);
        parent.transform.position = position;
        parent.transform.rotation = Quaternion.Euler(0f, yRotation, 0f);

        CreateVisualPrimitive(
            PrimitiveType.Cube,
            "Barrier_Body",
            Vector3.up * 0.22f,
            new Vector3(1.2f, 0.34f, 0.16f),
            Vector3.zero,
            metalMat,
            parent.transform
        );

        CreateVisualPrimitive(
            PrimitiveType.Cube,
            "Barrier_Stripe",
            Vector3.up * 0.32f,
            new Vector3(1.22f, 0.07f, 0.17f),
            Vector3.zero,
            routeMat,
            parent.transform
        );
    }

    private void PolishLighting(Bounds bounds)
    {
        RenderSettings.ambientLight = new Color(0.18f, 0.18f, 0.20f);
        RenderSettings.fog = true;
        RenderSettings.fogColor = new Color(0.12f, 0.12f, 0.13f);
        RenderSettings.fogDensity = 0.010f;

        Light mainLight = FindObjectOfType<Light>();

        if (mainLight != null)
        {
            mainLight.type = LightType.Directional;
            mainLight.intensity = 0.90f;
            mainLight.color = new Color(1f, 0.92f, 0.78f);
            mainLight.transform.rotation = Quaternion.Euler(50f, -35f, 0f);
            mainLight.shadows = LightShadows.Soft;
        }

        CreatePointLight(
            "Red_Emergency_Light",
            bounds.center + new Vector3(-bounds.extents.x * 0.6f, 2.4f, bounds.extents.z * 0.6f),
            dangerColor,
            1.4f,
            7f
        );

        CreatePointLight(
            "Amber_Route_Light",
            bounds.center + new Vector3(bounds.extents.x * 0.55f, 2.6f, -bounds.extents.z * 0.55f),
            routeColor,
            1.2f,
            7f
        );
    }

    private void PolishCamera(Bounds bounds)
    {
        Camera cam = Camera.main;

        if (cam == null)
            return;

        Vector3 center = bounds.center;

        // Ángulo como el que pediste:
        // más cerca, vista elevada, pero no tan alejada ni tan rara.
        cam.transform.position = center + new Vector3(0f, 12.5f, -11.5f);

        cam.transform.LookAt(
            center + new Vector3(0f, 0f, 0.8f)
        );

        cam.fieldOfView = 50f;
    }

    private void CreateDynamicRobotTrail()
    {
        robot = FindRobot();

        if (robot == null)
        {
            Debug.LogWarning("RescueTwinVisualPolish: no pude crear recorrido dinámico porque no encontré Robot.");
            return;
        }

        GameObject trailObject = new GameObject("Robot_Trail_Amber");
        trailObject.transform.SetParent(visualsRoot, false);

        dynamicTrail = trailObject.AddComponent<LineRenderer>();
        dynamicTrail.useWorldSpace = true;
        dynamicTrail.loop = false;
        dynamicTrail.material = routeMat;
        dynamicTrail.startColor = routeColor;
        dynamicTrail.endColor = routeColor;
        dynamicTrail.startWidth = dynamicTrailWidth;
        dynamicTrail.endWidth = dynamicTrailWidth;
        dynamicTrail.numCapVertices = 10;
        dynamicTrail.numCornerVertices = 10;
        dynamicTrail.shadowCastingMode = ShadowCastingMode.Off;
        dynamicTrail.receiveShadows = false;
        dynamicTrail.positionCount = 0;

        trailPoints.Clear();
        AddTrailPoint(GetRobotTrailPosition());
    }

    private void UpdateDynamicTrail()
    {
        if (robot == null)
        {
            robot = FindRobot();
        }

        if (robot == null || dynamicTrail == null)
            return;

        Vector3 current = GetRobotTrailPosition();

        if (trailPoints.Count == 0)
        {
            AddTrailPoint(current);
            return;
        }

        Vector3 last = trailPoints[trailPoints.Count - 1];
        float distance = Vector3.Distance(last, current);

        if (distance > teleportResetDistance)
        {
            trailPoints.Clear();
            dynamicTrail.positionCount = 0;
            AddTrailPoint(current);
            return;
        }

        if (distance >= minTrailDistance)
        {
            AddTrailPoint(current);
        }
    }

    private Vector3 GetRobotTrailPosition()
    {
        Vector3 p = robot.position;
        p.y = trailY + 0.10f;
        return p;
    }

    private void AddTrailPoint(Vector3 point)
    {
        trailPoints.Add(point);
        dynamicTrail.positionCount = trailPoints.Count;
        dynamicTrail.SetPosition(trailPoints.Count - 1, point);
    }

    private Transform FindRobot()
    {
        GameObject[] all = FindObjectsOfType<GameObject>(true);

        // Primero buscamos el perro robot específicamente.
        foreach (GameObject obj in all)
        {
            string n = obj.name.ToLower();

            if (
                n.Contains("dog") ||
                n.Contains("perro") ||
                n.Contains("quadruped") ||
                n.Contains("searchdog")
            )
            {
                if (obj.GetComponentInChildren<Renderer>(true) != null)
                {
                    return obj.transform;
                }
            }
        }

        // Si no existe un objeto con nombre de perro, usamos Robot.
        GameObject direct = GameObject.Find("Robot");

        if (direct != null)
            return direct.transform;

        // Último fallback.
        foreach (GameObject obj in all)
        {
            string n = obj.name.ToLower();

            if (n.Contains("robot"))
            {
                if (obj.GetComponentInChildren<Renderer>(true) != null)
                {
                    return obj.transform;
                }
            }
        }

        return null;
    }

    private GameObject CreateVisualCube(
        string name,
        Vector3 position,
        Vector3 scale,
        Vector3 euler,
        Material mat
    )
    {
        return CreateVisualPrimitive(
            PrimitiveType.Cube,
            name,
            position,
            scale,
            euler,
            mat
        );
    }

    private GameObject CreateVisualPrimitive(
        PrimitiveType type,
        string name,
        Vector3 position,
        Vector3 scale,
        Vector3 euler,
        Material mat,
        Transform customParent = null
    )
    {
        Transform parent = customParent != null ? customParent : visualsRoot;

        GameObject go = GameObject.CreatePrimitive(type);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.position = position;
        go.transform.localScale = scale;
        go.transform.rotation = Quaternion.Euler(euler);

        Renderer r = go.GetComponent<Renderer>();

        if (r != null)
        {
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.On;
            r.receiveShadows = true;
        }

        RemoveCollider(go);

        return go;
    }

    private void ApplyMaterial(GameObject go, Material mat)
    {
        Renderer r = go.GetComponent<Renderer>();

        if (r != null)
        {
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.On;
            r.receiveShadows = true;
        }
    }

    private void ApplyFlatMaterial(GameObject go, Material mat)
    {
        Renderer r = go.GetComponent<Renderer>();

        if (r != null)
        {
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
        }
    }

    private void CreatePointLight(
        string name,
        Vector3 position,
        Color color,
        float intensity,
        float range
    )
    {
        GameObject lightObject = new GameObject(name);
        lightObject.transform.SetParent(visualsRoot, false);
        lightObject.transform.position = position;

        Light l = lightObject.AddComponent<Light>();
        l.type = LightType.Point;
        l.color = color;
        l.intensity = intensity;
        l.range = range;
        l.shadows = LightShadows.Soft;
    }

    private Bounds GetObjectBounds(GameObject obj)
    {
        Renderer r = obj.GetComponent<Renderer>();

        if (r != null)
            return r.bounds;

        Renderer[] renderers = obj.GetComponentsInChildren<Renderer>(true);

        if (renderers.Length == 0)
            return new Bounds(obj.transform.position, new Vector3(12f, 1f, 12f));

        Bounds b = renderers[0].bounds;

        for (int i = 1; i < renderers.Length; i++)
        {
            b.Encapsulate(renderers[i].bounds);
        }

        return b;
    }

    private Material CreateMaterial(
        string name,
        Color color,
        float emissionIntensity,
        bool lit
    )
    {
        Shader shader;

        if (lit)
        {
            shader = Shader.Find("Universal Render Pipeline/Lit");

            if (shader == null)
                shader = Shader.Find("Standard");
        }
        else
        {
            shader = Shader.Find("Universal Render Pipeline/Unlit");

            if (shader == null)
                shader = Shader.Find("Unlit/Color");

            if (shader == null)
                shader = Shader.Find("Standard");
        }

        Material mat = new Material(shader);
        mat.name = name;

        if (mat.HasProperty("_BaseColor"))
            mat.SetColor("_BaseColor", color);

        if (mat.HasProperty("_Color"))
            mat.SetColor("_Color", color);

        mat.color = color;

        if (emissionIntensity > 0f && mat.HasProperty("_EmissionColor"))
        {
            mat.EnableKeyword("_EMISSION");
            mat.SetColor("_EmissionColor", color * emissionIntensity);
        }

        return mat;
    }

    private void RemoveCollider(GameObject go)
    {
        Collider c = go.GetComponent<Collider>();

        if (c != null)
        {
            SafeDestroy(c);
        }
    }

    private void ClearObstacleDetailRoots()
    {
        Transform[] transforms = FindObjectsOfType<Transform>(true);

        foreach (Transform t in transforms)
        {
            if (t.name == "__ObstacleDetailChunks__")
            {
                SafeDestroy(t.gameObject);
            }
        }
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