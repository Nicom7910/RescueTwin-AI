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

    // No usamos "base" porque es palabra reservada en C#.
    public WorldPoint base_point;

    public List<WorldPoint> obstacles;
    public List<WorldPoint> victims;
    public List<RiskCell> risk_cells;
}

public class MissionMapBuilder : MonoBehaviour
{
    [Header("World file")]
    public string worldFileName = "mission_001_world.json";

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

    private void Start()
    {
        LoadWorld();
        BuildMap();
    }

    private void LoadWorld()
    {
        string path = Path.Combine(Application.streamingAssetsPath, worldFileName);

        if (!File.Exists(path))
        {
            Debug.LogError("No se encontró el archivo de mundo para Unity: " + path);
            return;
        }

        string json = File.ReadAllText(path);

        // El JSON generado por Python tiene una clave llamada "base".
        // En C# no podemos declarar una variable llamada "base",
        // entonces la adaptamos antes de parsear.
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
            "Mundo cargado correctamente. " +
            "Obstáculos: " + SafeCount(worldData.obstacles) +
            " | Víctimas: " + SafeCount(worldData.victims) +
            " | Riesgos: " + SafeCount(worldData.risk_cells)
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
                Destroy(existing);
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

        ground.transform.position = Vector3.zero;
        ground.transform.localScale = new Vector3(2.2f, 1f, 2.2f);

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

        for (int x = 0; x <= mapWidth; x++)
        {
            Vector3 start = GridToWorldRaw(x, 0);
            Vector3 end = GridToWorldRaw(x, mapHeight);

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

        for (int y = 0; y <= mapHeight; y++)
        {
            Vector3 start = GridToWorldRaw(0, y);
            Vector3 end = GridToWorldRaw(mapWidth, y);

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

    private Vector3 GridToWorldRaw(int x, int y)
    {
        float worldX = (x - mapWidth / 2f) * cellSize;
        float worldZ = (y - mapHeight / 2f) * cellSize;

        return new Vector3(worldX, 0.04f, worldZ);
    }
}