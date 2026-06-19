using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

[Serializable]
public class WorldPoint
{
    public int x;
    public int y;
}

[Serializable]
public class RiskCell
{
    public int x;
    public int y;
    public string level;
    public float score;
    public float gas;
    public float temperature;
    public float vibration;
    public float inclination;
}

[Serializable]
public class UnityWorldData
{
    public int mission;
    public int width;
    public int height;
    public WorldPoint base_point;
    public List<WorldPoint> obstacles;
    public List<WorldPoint> victims;
    public List<RiskCell> risk_cells;
}

[Serializable]
public class MapTrajectoryStep
{
    public int step;
    public int x;
    public int y;
    public string action;
    public string risk_level;
    public string battery_level;
    public bool escape_mode;
    public bool return_to_base_mode;
}

[Serializable]
public class MapTrajectoryStepList
{
    public List<MapTrajectoryStep> steps;
}

public class MissionMapBuilder : MonoBehaviour
{
    [Header("World file")]
    public string worldFileName = "demo_001_world.json";

    [Header("Trajectory focus")]
    public string trajectoryFileName = "demo_001_trajectory.json";
    public bool focusOnTrajectory = true;
    public int focusMargin = 3;

    [Header("Map settings")]
    public int mapWidth = 20;
    public int mapHeight = 20;
    public float cellSize = 1.0f;

    [Header("Prefabs opcionales")]
    public GameObject obstaclePrefab;
    public GameObject victimPrefab;
    public GameObject riskCellPrefab;

    [Header("Visual settings")]
    public bool generateGrid = true;
    public bool generateObstacles = true;
    public bool generateRiskCells = true;
    public bool generateVictimMarkers = true;

    [Header("Materials")]
    public Material groundMaterial;
    public Material gridMaterial;
    public Material obstacleMaterial;
    public Material mediumRiskMaterial;
    public Material highRiskMaterial;
    public Material victimMaterial;

    private UnityWorldData worldData;

    private int focusMinX = 0;
    private int focusMaxX = 19;
    private int focusMinY = 0;
    private int focusMaxY = 19;
    private bool hasFocusBounds = false;

    private void Start()
    {
        LoadAndBuildWorld(worldFileName, trajectoryFileName);
    }

    public void LoadAndBuildWorld(string newWorldFileName, string newTrajectoryFileName)
    {
        worldFileName = newWorldFileName;
        trajectoryFileName = newTrajectoryFileName;

        LoadWorld();
        LoadTrajectoryFocusBounds();
        BuildMap();
    }

    private void LoadWorld()
    {
        string path = Path.Combine(Application.streamingAssetsPath, worldFileName);

        if (!File.Exists(path))
        {
            Debug.LogError("No se encontró el archivo de mundo para Unity: " + path);
            worldData = null;
            return;
        }

        string json = File.ReadAllText(path);

        // Python exporta "base", pero "base" es palabra reservada en C#.
        json = json.Replace("\"base\"", "\"base_point\"");

        worldData = JsonUtility.FromJson<UnityWorldData>(json);

        if (worldData == null)
        {
            Debug.LogError("No se pudo parsear el archivo de mundo: " + worldFileName);
            return;
        }

        mapWidth = worldData.width;
        mapHeight = worldData.height;

        Debug.Log(
            "Mundo cargado correctamente: " + worldFileName +
            " | Obstáculos: " + SafeCount(worldData.obstacles) +
            " | Víctimas: " + SafeCount(worldData.victims) +
            " | Riesgos: " + SafeCount(worldData.risk_cells)
        );
    }

    private void LoadTrajectoryFocusBounds()
    {
        hasFocusBounds = false;

        if (!focusOnTrajectory)
        {
            focusMinX = 0;
            focusMaxX = mapWidth - 1;
            focusMinY = 0;
            focusMaxY = mapHeight - 1;
            hasFocusBounds = true;
            return;
        }

        string path = Path.Combine(Application.streamingAssetsPath, trajectoryFileName);

        if (!File.Exists(path))
        {
            Debug.LogWarning("No se encontró trayectoria para enfocar mapa: " + path);
            focusMinX = 0;
            focusMaxX = mapWidth - 1;
            focusMinY = 0;
            focusMaxY = mapHeight - 1;
            hasFocusBounds = true;
            return;
        }

        string json = File.ReadAllText(path);
        string wrappedJson = "{\"steps\":" + json + "}";

        MapTrajectoryStepList loaded = JsonUtility.FromJson<MapTrajectoryStepList>(wrappedJson);

        if (loaded == null || loaded.steps == null || loaded.steps.Count == 0)
        {
            focusMinX = 0;
            focusMaxX = mapWidth - 1;
            focusMinY = 0;
            focusMaxY = mapHeight - 1;
            hasFocusBounds = true;
            return;
        }

        int minX = mapWidth;
        int maxX = 0;
        int minY = mapHeight;
        int maxY = 0;

        foreach (MapTrajectoryStep step in loaded.steps)
        {
            minX = Mathf.Min(minX, step.x);
            maxX = Mathf.Max(maxX, step.x);
            minY = Mathf.Min(minY, step.y);
            maxY = Mathf.Max(maxY, step.y);
        }

        if (worldData != null && worldData.base_point != null)
        {
            minX = Mathf.Min(minX, worldData.base_point.x);
            maxX = Mathf.Max(maxX, worldData.base_point.x);
            minY = Mathf.Min(minY, worldData.base_point.y);
            maxY = Mathf.Max(maxY, worldData.base_point.y);
        }

        focusMinX = Mathf.Clamp(minX - focusMargin, 0, mapWidth - 1);
        focusMaxX = Mathf.Clamp(maxX + focusMargin, 0, mapWidth - 1);
        focusMinY = Mathf.Clamp(minY - focusMargin, 0, mapHeight - 1);
        focusMaxY = Mathf.Clamp(maxY + focusMargin, 0, mapHeight - 1);

        hasFocusBounds = true;

        Debug.Log(
            "Mapa enfocado en trayectoria: " +
            $"X[{focusMinX},{focusMaxX}] Y[{focusMinY},{focusMaxY}]"
        );
    }

    private int SafeCount<T>(List<T> list)
    {
        return list == null ? 0 : list.Count;
    }

    public void BuildMap()
    {
        ClearGeneratedObjects();
        CreateGround();

        if (generateGrid)
        {
            CreateGrid();
        }

        if (worldData == null)
        {
            return;
        }

        if (generateRiskCells)
        {
            CreateRiskCellsFromWorld();
        }

        if (generateObstacles)
        {
            CreateObstaclesFromWorld();
        }

        if (generateVictimMarkers)
        {
            CreateVictimMarkersFromWorld();
        }
    }

    private void ClearGeneratedObjects()
    {
        string[] names =
        {
            "Generated Grid",
            "Generated Obstacles",
            "Generated Risk Cells",
            "Generated Victim Markers"
        };

        foreach (string objectName in names)
        {
            GameObject existing = GameObject.Find(objectName);

            if (existing != null)
            {
                if (Application.isPlaying)
                {
                    Destroy(existing);
                }
                else
                {
                    DestroyImmediate(existing);
                }
            }
        }
    }

    private void CreateGround()
    {
        GameObject ground = GameObject.Find("Ground");

        if (ground == null)
        {
            ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.name = "Ground";
        }

        float minWorldX = GridLineToWorldX(focusMinX);
        float maxWorldX = GridLineToWorldX(focusMaxX + 1);
        float minWorldZ = GridLineToWorldZ(focusMinY);
        float maxWorldZ = GridLineToWorldZ(focusMaxY + 1);

        float centerX = (minWorldX + maxWorldX) / 2f;
        float centerZ = (minWorldZ + maxWorldZ) / 2f;

        float width = Mathf.Max(1f, Mathf.Abs(maxWorldX - minWorldX));
        float height = Mathf.Max(1f, Mathf.Abs(maxWorldZ - minWorldZ));

        ground.transform.position = new Vector3(centerX, 0f, centerZ);
        ground.transform.localScale = new Vector3(width / 10f, 1f, height / 10f);

        Renderer renderer = ground.GetComponent<Renderer>();

        if (renderer != null && groundMaterial != null)
        {
            renderer.material = groundMaterial;
        }
        else if (renderer != null)
        {
            renderer.material.color = new Color(0.28f, 0.25f, 0.22f);
        }
    }

    private void CreateGrid()
    {
        GameObject gridParent = new GameObject("Generated Grid");

        int startX = hasFocusBounds ? focusMinX : 0;
        int endX = hasFocusBounds ? focusMaxX + 1 : mapWidth;
        int startY = hasFocusBounds ? focusMinY : 0;
        int endY = hasFocusBounds ? focusMaxY + 1 : mapHeight;

        for (int x = startX; x <= endX; x++)
        {
            Vector3 start = GridLineToWorld(x, startY);
            Vector3 end = GridLineToWorld(x, endY);

            CreateLine(
                gridParent.transform,
                "Grid Line X",
                start,
                end,
                0.025f,
                new Color(0.65f, 0.65f, 0.65f, 0.35f),
                gridMaterial
            );
        }

        for (int y = startY; y <= endY; y++)
        {
            Vector3 start = GridLineToWorld(startX, y);
            Vector3 end = GridLineToWorld(endX, y);

            CreateLine(
                gridParent.transform,
                "Grid Line Y",
                start,
                end,
                0.025f,
                new Color(0.65f, 0.65f, 0.65f, 0.35f),
                gridMaterial
            );
        }
    }

    private void CreateObstaclesFromWorld()
    {
        GameObject parent = new GameObject("Generated Obstacles");

        if (worldData.obstacles == null)
        {
            return;
        }

        foreach (WorldPoint point in worldData.obstacles)
        {
            if (!IsInsideFocus(point.x, point.y))
            {
                continue;
            }

            GameObject obstacle;

            if (obstaclePrefab != null)
            {
                obstacle = Instantiate(obstaclePrefab, parent.transform);
            }
            else
            {
                obstacle = GameObject.CreatePrimitive(PrimitiveType.Cube);
                obstacle.transform.SetParent(parent.transform);
            }

            obstacle.name = "Obstacle_" + point.x + "_" + point.y;
            obstacle.transform.position = GridToWorld(point.x, point.y, 0.45f);

            float height = UnityEngine.Random.Range(0.55f, 1.25f);
            obstacle.transform.localScale = new Vector3(0.85f, height, 0.85f);

            Renderer renderer = obstacle.GetComponent<Renderer>();

            if (renderer != null && obstacleMaterial != null)
            {
                renderer.material = obstacleMaterial;
            }
            else if (renderer != null)
            {
                renderer.material.color = new Color(0.22f, 0.22f, 0.22f);
            }
        }
    }

    private void CreateRiskCellsFromWorld()
    {
        GameObject parent = new GameObject("Generated Risk Cells");

        if (worldData.risk_cells == null)
        {
            return;
        }

        foreach (RiskCell cell in worldData.risk_cells)
        {
            if (!IsInsideFocus(cell.x, cell.y))
            {
                continue;
            }

            GameObject riskCell;

            if (riskCellPrefab != null)
            {
                riskCell = Instantiate(riskCellPrefab, parent.transform);
            }
            else
            {
                riskCell = GameObject.CreatePrimitive(PrimitiveType.Cube);
                riskCell.transform.SetParent(parent.transform);
            }

            riskCell.name = "RiskCell_" + cell.level + "_" + cell.x + "_" + cell.y;
            riskCell.transform.position = GridToWorld(cell.x, cell.y, 0.035f);
            riskCell.transform.localScale = new Vector3(0.92f, 0.025f, 0.92f);

            Renderer renderer = riskCell.GetComponent<Renderer>();

            if (renderer == null)
            {
                continue;
            }

            if (cell.level == "ALTO")
            {
                if (highRiskMaterial != null)
                {
                    renderer.material = highRiskMaterial;
                }
                else
                {
                    renderer.material.color = new Color(1f, 0.1f, 0.1f);
                }
            }
            else
            {
                if (mediumRiskMaterial != null)
                {
                    renderer.material = mediumRiskMaterial;
                }
                else
                {
                    renderer.material.color = new Color(1f, 0.75f, 0.05f);
                }
            }
        }
    }

    private void CreateVictimMarkersFromWorld()
    {
        GameObject parent = new GameObject("Generated Victim Markers");

        if (worldData.victims == null)
        {
            return;
        }

        foreach (WorldPoint point in worldData.victims)
        {
            if (!IsInsideFocus(point.x, point.y))
            {
                continue;
            }

            GameObject victim;

            if (victimPrefab != null)
            {
                victim = Instantiate(victimPrefab, parent.transform);
            }
            else
            {
                victim = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                victim.transform.SetParent(parent.transform);
            }

            victim.name = "VictimMarker_" + point.x + "_" + point.y;
            victim.transform.position = GridToWorld(point.x, point.y, 0.42f);
            victim.transform.localScale = new Vector3(0.45f, 0.45f, 0.45f);

            Renderer renderer = victim.GetComponent<Renderer>();

            if (renderer != null && victimMaterial != null)
            {
                renderer.material = victimMaterial;
            }
            else if (renderer != null)
            {
                renderer.material.color = Color.magenta;
            }
        }
    }

    private bool IsInsideFocus(int x, int y)
    {
        if (!hasFocusBounds)
        {
            return true;
        }

        return x >= focusMinX && x <= focusMaxX && y >= focusMinY && y <= focusMaxY;
    }

    private void CreateLine(
        Transform parent,
        string name,
        Vector3 start,
        Vector3 end,
        float width,
        Color color,
        Material material
    )
    {
        GameObject lineObject = new GameObject(name);
        lineObject.transform.SetParent(parent);

        LineRenderer line = lineObject.AddComponent<LineRenderer>();
        line.positionCount = 2;
        line.SetPosition(0, start);
        line.SetPosition(1, end);
        line.widthMultiplier = width;
        line.useWorldSpace = true;

        if (material != null)
        {
            line.material = material;
        }
        else
        {
            line.material = new Material(Shader.Find("Sprites/Default"));
            line.material.color = color;
        }
    }

    private Vector3 GridToWorld(int x, int y, float height)
    {
        float worldX = (x - mapWidth / 2f) * cellSize;
        float worldZ = (y - mapHeight / 2f) * cellSize;

        return new Vector3(worldX, height, worldZ);
    }

    private Vector3 GridLineToWorld(int x, int y)
    {
        return new Vector3(GridLineToWorldX(x), 0.04f, GridLineToWorldZ(y));
    }

    private float GridLineToWorldX(int x)
    {
        return (x - mapWidth / 2f) * cellSize;
    }

    private float GridLineToWorldZ(int y)
    {
        return (y - mapHeight / 2f) * cellSize;
    }
}