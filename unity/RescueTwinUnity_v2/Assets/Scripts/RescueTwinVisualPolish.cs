using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

public class RescueTwinVisualPolish : MonoBehaviour
{
    [Header("General")]
    public bool buildOnStart = true;

    [Header("Overlay digital")]
    public bool showDigitalGrid = true;
    public float gridSpacing = 1f;
    public float gridThickness = 0.0045f;
    public Color gridColor = new Color(0.04f, 0.42f, 0.50f);

    [Header("Ruta del robot")]
    public Color routeColor = new Color(1f, 0.72f, 0.10f);
    public float routeWidth = 0.18f;
    public float dynamicTrailWidth = 0.22f;
    public float minTrailDistance = 0.20f;
    public float teleportResetDistance = 4.5f;

    [Header("Piso")]
    public Color floorColor = new Color(0.105f, 0.105f, 0.11f);
    public Color dustColor = new Color(0.30f, 0.29f, 0.27f);
    public Color crackColor = new Color(0.025f, 0.025f, 0.028f);

    [Header("Paredes")]
    public float wallHeight = 1.25f;
    public float wallThickness = 0.22f;
    public float wallMargin = 0.25f;
    public Color wallColor = new Color(0.42f, 0.39f, 0.36f);

    [Header("Obstáculos y escombros")]
    public bool improveObstacles = true;
    public bool generateRubble = true;
    public int rubbleSeed = 77;
    public Color concreteColor = new Color(0.56f, 0.54f, 0.50f);
    public Color darkConcreteColor = new Color(0.33f, 0.32f, 0.30f);
    public Color metalColor = new Color(0.28f, 0.30f, 0.32f);

    [Header("Víctimas")]
    public Color victimSkinColor = new Color(0.85f, 0.68f, 0.55f);
    public Color victimClothColor = new Color(0.85f, 0.45f, 0.10f);
    public Color victimFallbackBeaconColor = new Color(0.85f, 0.20f, 0.85f);
    public float victimScale = 3.6f;

    private Transform visualsRoot;

    private Material floorMat;
    private Material gridMat;
    private Material routeMat;
    private Material wallMat;
    private Material dustMat;
    private Material crackMat;
    private Material concreteMat;
    private Material darkConcreteMat;
    private Material metalMat;
    private Material panelMat;
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
        Random.InitState(rubbleSeed);

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
        HideDangerZonesCompletely();

        BuildFloorDamageMarks(groundBounds);

        if (showDigitalGrid)
            BuildSubtleDigitalGrid(groundBounds);

        PolishExistingRoute();
        PolishVictims();

        if (improveObstacles)
            ImproveExistingObstacles();

        if (generateRubble)
            BuildBetterRubble(groundBounds);

        BuildPerimeterWalls(groundBounds);
        PolishLighting(groundBounds);
        PolishCamera(groundBounds);
        CreateDynamicRobotTrail();

        Debug.Log("RescueTwinVisualPolish aplicado: piso, sombras, escombros y ruta mejorados.");
    }

    private void CleanOldGeneratedObjects()
    {
        string[] names =
        {
            "__VisualPolishRoot__",
            "Generated_Tactical_Rescue_Visuals",
            "Generated_Rescue_Visuals",
            "GeneratedRubbleVisuals",
            "GeneratedEnvironmentVisuals",
            "Robot_Trail_Cyan",
            "Robot_Trail_Amber",
            "RobotTrail"
        };

        foreach (string n in names)
        {
            GameObject obj = GameObject.Find(n);

            if (obj != null)
                SafeDestroy(obj);
        }

        GameObject[] all = FindObjectsOfType<GameObject>(true);

        foreach (GameObject obj in all)
        {
            if (obj.name.StartsWith("Label_"))
                SafeDestroy(obj);

            if (obj.name == "__ObstacleDetails__")
                SafeDestroy(obj);
        }
    }

    private void EnsureRoot()
    {
        GameObject root = new GameObject("__VisualPolishRoot__");
        root.transform.SetParent(transform, false);
        visualsRoot = root.transform;
    }

    private void PrepareMaterials()
    {
        floorMat = CreateMaterial("Mat_Dark_Damaged_Concrete_Floor", floorColor, 0f, true, 0.18f);
        gridMat = CreateMaterial("Mat_Subtle_Digital_Grid", gridColor, 0.28f, false, 0.0f);
        routeMat = CreateMaterial("Mat_Robot_Route_Amber", routeColor, 2.3f, false, 0.0f);

        wallMat = CreateMaterial("Mat_Damaged_Wall", wallColor, 0f, true, 0.08f);
        dustMat = CreateMaterial("Mat_Dust_Overlay", dustColor, 0f, true, 0.0f);
        crackMat = CreateMaterial("Mat_Floor_Cracks", crackColor, 0f, true, 0.0f);

        concreteMat = CreateMaterial("Mat_Broken_Concrete", concreteColor, 0f, true, 0.06f);
        darkConcreteMat = CreateMaterial("Mat_Dark_Broken_Concrete", darkConcreteColor, 0f, true, 0.04f);
        metalMat = CreateMaterial("Mat_Damaged_Metal", metalColor, 0f, true, 0.12f);
        panelMat = CreateMaterial("Mat_Obstacle_Panel", new Color(0.20f, 0.21f, 0.22f), 0f, true, 0.08f);

        victimSkinMat = CreateMaterial("Mat_Victim_Skin", victimSkinColor, 0f, true, 0.2f);
        victimClothMat = CreateMaterial("Mat_Victim_Cloth", victimClothColor, 0f, true, 0.15f);
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

    private void HideDangerZonesCompletely()
    {
        Renderer[] renderers = FindObjectsOfType<Renderer>(true);

        foreach (Renderer r in renderers)
        {
            if (r == null)
                continue;

            if (visualsRoot != null && r.transform.IsChildOf(visualsRoot))
                continue;

            string n = r.gameObject.name.ToLower();

            bool isDanger =
                n.Contains("risk") ||
                n.Contains("danger") ||
                n.Contains("alto") ||
                n.Contains("hazard") ||
                n.Contains("red");

            if (isDanger)
                r.enabled = false;
        }
    }

    private void BuildFloorDamageMarks(Bounds bounds)
    {
        for (int i = 0; i < 26; i++)
        {
            Vector3 pos = RandomPointInside(bounds);
            pos.y = bounds.max.y + 0.018f;

            Vector3 scale = new Vector3(
                Random.Range(0.35f, 1.4f),
                0.005f,
                Random.Range(0.18f, 0.80f)
            );

            CreateFlatCube(
                "Dust_Mark",
                pos,
                scale,
                new Vector3(0f, Random.Range(0f, 360f), 0f),
                dustMat
            );
        }

        for (int i = 0; i < 20; i++)
        {
            Vector3 pos = RandomPointInside(bounds);
            pos.y = bounds.max.y + 0.024f;

            Vector3 scale = new Vector3(
                Random.Range(0.45f, 1.35f),
                0.006f,
                Random.Range(0.018f, 0.045f)
            );

            CreateFlatCube(
                "Floor_Crack",
                pos,
                scale,
                new Vector3(0f, Random.Range(0f, 360f), 0f),
                crackMat
            );

            if (Random.value > 0.45f)
            {
                Vector3 branchPos = pos + new Vector3(
                    Random.Range(-0.18f, 0.18f),
                    0.002f,
                    Random.Range(-0.18f, 0.18f)
                );

                Vector3 branchScale = new Vector3(
                    Random.Range(0.25f, 0.70f),
                    0.006f,
                    Random.Range(0.015f, 0.035f)
                );

                CreateFlatCube(
                    "Floor_Crack_Branch",
                    branchPos,
                    branchScale,
                    new Vector3(0f, Random.Range(0f, 360f), 0f),
                    crackMat
                );
            }
        }
    }

    private void BuildSubtleDigitalGrid(Bounds bounds)
    {
        float y = bounds.max.y + 0.038f;

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
        GameObject obj = new GameObject("Subtle_Digital_Grid_Line");
        obj.transform.SetParent(visualsRoot, false);

        LineRenderer line = obj.AddComponent<LineRenderer>();
        line.useWorldSpace = true;
        line.positionCount = 2;
        line.SetPosition(0, start);
        line.SetPosition(1, end);

        line.startWidth = gridThickness;
        line.endWidth = gridThickness;

        line.material = gridMat;
        line.startColor = new Color(gridColor.r, gridColor.g, gridColor.b, 0.28f);
        line.endColor = new Color(gridColor.r, gridColor.g, gridColor.b, 0.28f);

        line.numCornerVertices = 1;
        line.numCapVertices = 1;
        line.shadowCastingMode = ShadowCastingMode.Off;
        line.receiveShadows = false;
    }

    private void ImproveExistingObstacles()
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

            if (ShouldSkipObstacle(n, obj))
                continue;

            BoxCollider box = obj.GetComponent<BoxCollider>();

            if (box == null)
                continue;

            Bounds b = r.bounds;

            if (b.size.x > 3.8f || b.size.y > 3.8f || b.size.z > 3.8f)
                continue;

            bool dark = Random.value > 0.45f;
            r.sharedMaterial = dark ? darkConcreteMat : concreteMat;
            r.shadowCastingMode = ShadowCastingMode.On;
            r.receiveShadows = true;

            AddObstacleDetails(obj.transform, box);
        }
    }

    private bool ShouldSkipObstacle(string name, GameObject obj)
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
        if (name.Contains("visual")) return true;
        if (name.Contains("polish")) return true;
        if (name.Contains("generated")) return true;
        if (name.Contains("__")) return true;

        Renderer renderer = obj.GetComponent<Renderer>();

        if (renderer == null)
            return true;

        return false;
    }

    private void AddObstacleDetails(Transform obstacle, BoxCollider box)
    {
        Transform old = obstacle.Find("__ObstacleDetails__");

        if (old != null)
            SafeDestroy(old.gameObject);

        GameObject root = new GameObject("__ObstacleDetails__");
        root.transform.SetParent(obstacle, false);
        root.transform.localPosition = Vector3.zero;
        root.transform.localRotation = Quaternion.identity;
        root.transform.localScale = Vector3.one;

        Vector3 size = box.size;
        Vector3 center = box.center;

        if (size.y > 0.55f)
        {
            CreateLocalDetailCube(
                root.transform,
                "Front_Dark_Panel",
                center + new Vector3(0f, 0f, size.z * 0.515f),
                new Vector3(size.x * 0.30f, size.y * 0.16f, 0.035f),
                panelMat
            );

            CreateLocalDetailCube(
                root.transform,
                "Small_Handle",
                center + new Vector3(size.x * 0.18f, -size.y * 0.05f, size.z * 0.54f),
                new Vector3(size.x * 0.10f, size.y * 0.04f, 0.04f),
                metalMat
            );

            CreateLocalDetailCube(
                root.transform,
                "Top_Edge_Detail",
                center + new Vector3(0f, size.y * 0.515f, 0f),
                new Vector3(size.x * 0.82f, 0.035f, size.z * 0.82f),
                darkConcreteMat
            );
        }

        int chips = Random.Range(2, 5);

        for (int i = 0; i < chips; i++)
        {
            Vector3 localPos = center + new Vector3(
                Random.Range(-size.x * 0.42f, size.x * 0.42f),
                Random.Range(-size.y * 0.35f, size.y * 0.30f),
                size.z * 0.54f
            );

            Vector3 localScale = new Vector3(
                Random.Range(0.04f, 0.11f),
                Random.Range(0.04f, 0.12f),
                0.025f
            );

            CreateLocalDetailCube(
                root.transform,
                "Broken_Surface_Chip",
                localPos,
                localScale,
                Random.value > 0.5f ? darkConcreteMat : concreteMat
            );
        }
    }

    private GameObject CreateLocalDetailCube(
        Transform parent,
        string name,
        Vector3 localPos,
        Vector3 localScale,
        Material mat
    )
    {
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPos;
        go.transform.localRotation = Quaternion.Euler(
            Random.Range(-3f, 3f),
            Random.Range(-6f, 6f),
            Random.Range(-3f, 3f)
        );
        go.transform.localScale = localScale;

        ApplyMaterial(go, mat);
        RemoveCollider(go);

        return go;
    }

    private void BuildBetterRubble(Bounds bounds)
    {
        Vector3[] centers =
        {
            Point01(bounds, 0.22f, 0.32f),
            Point01(bounds, 0.58f, 0.41f),
            Point01(bounds, 0.55f, 0.72f),
            Point01(bounds, 0.80f, 0.26f),
            Point01(bounds, 0.28f, 0.70f),
            Point01(bounds, 0.72f, 0.64f)
        };

        foreach (Vector3 center in centers)
        {
            BuildCollapsedPile(center);
        }

        BuildCollapsedWallSection(Point01(bounds, 0.68f, 0.56f), 1.4f, 0.22f, 0.42f, 18f);
        BuildCollapsedWallSection(Point01(bounds, 0.38f, 0.58f), 1.2f, 0.20f, 0.38f, -22f);
        BuildCollapsedWallSection(Point01(bounds, 0.74f, 0.78f), 1.1f, 0.18f, 0.40f, 32f);
    }

    private void BuildCollapsedPile(Vector3 center)
    {
        int slabs = Random.Range(2, 4);

        for (int i = 0; i < slabs; i++)
            CreateRubbleSlab(center);

        int large = Random.Range(3, 5);

        for (int i = 0; i < large; i++)
            CreateRubbleChunk(center, 0.30f, 0.65f, 0.16f, 0.32f, 0.22f, 0.55f);

        int medium = Random.Range(9, 13);

        for (int i = 0; i < medium; i++)
            CreateRubbleChunk(center, 0.12f, 0.30f, 0.07f, 0.18f, 0.12f, 0.28f);

        int small = Random.Range(14, 20);

        for (int i = 0; i < small; i++)
            CreateSmallDebris(center);
    }

    private void CreateRubbleSlab(Vector3 center)
    {
        GameObject slab = GameObject.CreatePrimitive(PrimitiveType.Cube);
        slab.name = "Broken_Concrete_Slab";
        slab.transform.SetParent(visualsRoot, false);

        float sx = Random.Range(0.55f, 1.05f);
        float sy = Random.Range(0.055f, 0.12f);
        float sz = Random.Range(0.20f, 0.45f);

        Vector3 pos = center + new Vector3(
            Random.Range(-0.45f, 0.45f),
            0f,
            Random.Range(-0.35f, 0.35f)
        );

        slab.transform.position = pos + Vector3.up * (sy * 0.5f);
        slab.transform.rotation = Quaternion.Euler(
            Random.Range(-9f, 9f),
            Random.Range(0f, 180f),
            Random.Range(-9f, 9f)
        );
        slab.transform.localScale = new Vector3(sx, sy, sz);

        ApplyMaterial(slab, RandomConcreteMaterial());
        RemoveCollider(slab);
    }

    private void CreateRubbleChunk(
        Vector3 center,
        float minX,
        float maxX,
        float minY,
        float maxY,
        float minZ,
        float maxZ
    )
    {
        PrimitiveType type = Random.value > 0.72f ? PrimitiveType.Cylinder : PrimitiveType.Cube;

        GameObject piece = GameObject.CreatePrimitive(type);
        piece.name = "Broken_Rubble_Chunk";
        piece.transform.SetParent(visualsRoot, false);

        Vector3 scale;

        if (type == PrimitiveType.Cube)
        {
            scale = new Vector3(
                Random.Range(minX, maxX),
                Random.Range(minY, maxY),
                Random.Range(minZ, maxZ)
            );
        }
        else
        {
            float rad = Random.Range(minX * 0.35f, maxX * 0.38f);
            float h = Random.Range(minY, maxY);
            scale = new Vector3(rad, h, rad);
        }

        Vector3 pos = center + new Vector3(
            Random.Range(-0.55f, 0.55f),
            0f,
            Random.Range(-0.45f, 0.45f)
        );

        piece.transform.position = pos + Vector3.up * (scale.y * 0.5f);
        piece.transform.rotation = Quaternion.Euler(
            Random.Range(-20f, 20f),
            Random.Range(0f, 360f),
            Random.Range(-20f, 20f)
        );
        piece.transform.localScale = scale;

        ApplyMaterial(piece, RandomConcreteMaterial());
        RemoveCollider(piece);
    }

    private void CreateSmallDebris(Vector3 center)
    {
        PrimitiveType type = Random.value > 0.45f ? PrimitiveType.Cube : PrimitiveType.Sphere;

        GameObject piece = GameObject.CreatePrimitive(type);
        piece.name = "Small_Debris";
        piece.transform.SetParent(visualsRoot, false);

        float s = Random.Range(0.045f, 0.13f);

        piece.transform.localScale = new Vector3(
            s,
            s * Random.Range(0.75f, 1.25f),
            s * Random.Range(0.75f, 1.25f)
        );

        Vector3 pos = center + new Vector3(
            Random.Range(-0.70f, 0.70f),
            0f,
            Random.Range(-0.55f, 0.55f)
        );

        piece.transform.position = pos + Vector3.up * (piece.transform.localScale.y * 0.5f);
        piece.transform.rotation = Quaternion.Euler(
            Random.Range(-25f, 25f),
            Random.Range(0f, 360f),
            Random.Range(-25f, 25f)
        );

        ApplyMaterial(piece, RandomConcreteMaterial());
        RemoveCollider(piece);
    }

    private void BuildCollapsedWallSection(
        Vector3 center,
        float length,
        float thickness,
        float height,
        float yRotation
    )
    {
        GameObject wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
        wall.name = "Collapsed_Wall_Section";
        wall.transform.SetParent(visualsRoot, false);
        wall.transform.position = center + new Vector3(0f, height * 0.5f, 0f);
        wall.transform.rotation = Quaternion.Euler(-8f, yRotation, 6f);
        wall.transform.localScale = new Vector3(length, height, thickness);

        ApplyMaterial(wall, RandomConcreteMaterial());
        RemoveCollider(wall);

        for (int i = 0; i < 10; i++)
        {
            CreateSmallDebris(
                center + new Vector3(
                    Random.Range(-0.45f, 0.45f),
                    0f,
                    Random.Range(-0.40f, 0.40f)
                )
            );
        }
    }

    private Material RandomConcreteMaterial()
    {
        return Random.value > 0.42f ? concreteMat : darkConcreteMat;
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

    private void PolishExistingRoute()
    {
        LineRenderer[] lines = FindObjectsOfType<LineRenderer>(true);

        foreach (LineRenderer lr in lines)
        {
            if (lr == null)
                continue;

            if (visualsRoot != null && lr.transform.IsChildOf(visualsRoot))
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
            beaconColor = originalRenderer.sharedMaterial.color;

        if (originalRenderer != null)
            originalRenderer.enabled = false;

        Transform old = victimRoot.Find("__VictimFigure__");

        if (old != null)
            SafeDestroy(old.gameObject);

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
            1.5f,
            false,
            0f
        );

        ApplyMaterial(beacon, beaconMat);
        RemoveCollider(beacon);
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

    private void PolishLighting(Bounds bounds)
    {
        QualitySettings.shadows = ShadowQuality.All;
        QualitySettings.shadowDistance = 60f;

        RenderSettings.ambientLight = new Color(0.10f, 0.10f, 0.11f);
        RenderSettings.fog = true;
        RenderSettings.fogColor = new Color(0.09f, 0.09f, 0.10f);
        RenderSettings.fogDensity = 0.010f;

        Light[] lights = FindObjectsOfType<Light>(true);

        foreach (Light l in lights)
        {
            if (l == null)
                continue;

            if (l.type == LightType.Directional)
            {
                l.intensity = 0.95f;
                l.color = new Color(1f, 0.90f, 0.75f);
                l.shadows = LightShadows.Soft;
                l.shadowStrength = 0.85f;
                l.transform.rotation = Quaternion.Euler(52f, -36f, 0f);
            }
        }

        Camera cam = Camera.main;

        if (cam != null)
        {
            cam.backgroundColor = new Color(0.09f, 0.09f, 0.10f);
            cam.clearFlags = CameraClearFlags.SolidColor;
        }
    }

    private void PolishCamera(Bounds bounds)
    {
        Camera cam = Camera.main;

        if (cam == null)
            return;

        Vector3 center = bounds.center;

        cam.transform.position = center + new Vector3(0f, 12.5f, -11.5f);
        cam.transform.LookAt(center + new Vector3(0f, 0f, 0.8f));
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
            robot = FindRobot();

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
            AddTrailPoint(current);
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
        GameObject direct = GameObject.Find("Robot");

        if (direct != null)
            return direct.transform;

        GameObject[] all = FindObjectsOfType<GameObject>(true);

        foreach (GameObject obj in all)
        {
            string n = obj.name.ToLower();

            if (n.Contains("robot") || n.Contains("dog"))
                return obj.transform;
        }

        return null;
    }

    private Vector3 RandomPointInside(Bounds bounds)
    {
        return new Vector3(
            Random.Range(bounds.min.x + 0.8f, bounds.max.x - 0.8f),
            bounds.max.y,
            Random.Range(bounds.min.z + 0.8f, bounds.max.z - 0.8f)
        );
    }

    private Vector3 Point01(Bounds bounds, float nx, float nz)
    {
        float x = Mathf.Lerp(bounds.min.x + 1.0f, bounds.max.x - 1.0f, nx);
        float z = Mathf.Lerp(bounds.min.z + 1.0f, bounds.max.z - 1.0f, nz);
        float y = bounds.max.y + 0.015f;

        return new Vector3(x, y, z);
    }

    private GameObject CreateFlatCube(
        string name,
        Vector3 position,
        Vector3 scale,
        Vector3 euler,
        Material mat
    )
    {
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(visualsRoot, false);
        go.transform.position = position;
        go.transform.localScale = scale;
        go.transform.rotation = Quaternion.Euler(euler);

        ApplyFlatMaterial(go, mat);
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
            b.Encapsulate(renderers[i].bounds);

        return b;
    }

    private Material CreateMaterial(
        string name,
        Color color,
        float emissionIntensity,
        bool lit,
        float smoothness
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

        if (mat.HasProperty("_Smoothness"))
            mat.SetFloat("_Smoothness", smoothness);

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
            SafeDestroy(c);
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