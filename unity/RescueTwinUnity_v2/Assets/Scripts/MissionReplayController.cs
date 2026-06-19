using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

[Serializable]
public class MissionStep
{
    public int step;
    public int x;
    public int y;
    public string action;
    public string risk_level;
    public string battery_level;
    public string[] blocked_actions;
    public bool escape_mode;
    public bool return_to_base_mode;
}

[Serializable]
public class MissionStepList
{
    public List<MissionStep> steps;
}

public class MissionReplayController : MonoBehaviour
{
    [Header("Mission file")]
    public string missionFileName = "mission_001_trajectory.json";

    [Header("Scene references")]
    public Transform robot;
    public Transform baseMarker;

    [Header("Replay settings")]
    public float cellSize = 1.0f;
    public float stepDuration = 0.35f;
    public float robotHeight = 0.65f;
    public bool loopReplay = true;

    [Header("Map settings")]
    public int mapWidth = 20;
    public int mapHeight = 20;

    [Header("Visual trail")]
    public LineRenderer trailLine;

    private List<MissionStep> steps = new List<MissionStep>();
    private int currentIndex = 0;
    private float timer = 0f;
    private Vector3 startPosition;
    private Vector3 targetPosition;
    private MissionStep currentStep;

    private GUIStyle hudStyle;
    private GUIStyle titleStyle;
    private GUIStyle modeStyle;

    void Start()
    {
        LoadMission();

        if (robot == null)
        {
            Debug.LogError("No se asignó el robot en MissionReplayController.");
            return;
        }

        if (steps.Count == 0)
        {
            Debug.LogError("La misión no tiene pasos para reproducir.");
            return;
        }

        SetupBaseMarker();
        SetupTrail();
        SetupHudStyles();

        currentIndex = 0;
        currentStep = steps[currentIndex];

        Vector3 initialPosition = GridToWorld(currentStep.x, currentStep.y);
        robot.position = initialPosition;
        startPosition = initialPosition;
        targetPosition = initialPosition;

        ApplyRobotVisualState(currentStep);
        AddTrailPoint(initialPosition);
    }

    void Update()
    {
        if (robot == null || steps.Count == 0)
        {
            return;
        }

        timer += Time.deltaTime;
        float t = Mathf.Clamp01(timer / stepDuration);

        robot.position = Vector3.Lerp(startPosition, targetPosition, t);

        if (t >= 1f)
        {
            AdvanceStep();
        }
    }

    private void LoadMission()
    {
        string path = Path.Combine(Application.streamingAssetsPath, missionFileName);

        if (!File.Exists(path))
        {
            Debug.LogError("No se encontró el archivo de misión: " + path);
            return;
        }

        string json = File.ReadAllText(path);

        string wrappedJson = "{\"steps\":" + json + "}";

        MissionStepList loaded = JsonUtility.FromJson<MissionStepList>(wrappedJson);

        if (loaded != null && loaded.steps != null)
        {
            steps = loaded.steps;
            Debug.Log("Misión cargada correctamente. Pasos: " + steps.Count);
        }
        else
        {
            Debug.LogError("No se pudo parsear el archivo JSON de misión.");
        }
    }

    private void AdvanceStep()
    {
        currentIndex++;

        if (currentIndex >= steps.Count)
        {
            if (loopReplay)
            {
                currentIndex = 0;
                ClearTrail();
            }
            else
            {
                currentIndex = steps.Count - 1;
                return;
            }
        }

        currentStep = steps[currentIndex];

        startPosition = robot.position;
        targetPosition = GridToWorld(currentStep.x, currentStep.y);
        timer = 0f;

        RotateRobotByAction(currentStep.action);
        ApplyRobotVisualState(currentStep);
        AddTrailPoint(targetPosition);
    }

    private Vector3 GridToWorld(int x, int y)
    {
        float worldX = (x - mapWidth / 2f) * cellSize;
        float worldZ = (y - mapHeight / 2f) * cellSize;

        return new Vector3(worldX, robotHeight, worldZ);
    }

    private void SetupBaseMarker()
    {
        if (baseMarker == null)
        {
            return;
        }

        baseMarker.position = GridToWorld(10, 10);
        baseMarker.localScale = new Vector3(1.8f, 0.18f, 1.8f);

        Renderer renderer = baseMarker.GetComponent<Renderer>();

        if (renderer != null)
        {
            renderer.material.color = Color.blue;
        }
    }

    private void SetupTrail()
    {
        if (trailLine == null)
        {
            GameObject trailObject = new GameObject("Mission Trail");
            trailLine = trailObject.AddComponent<LineRenderer>();
            trailLine.widthMultiplier = 0.14f;
            trailLine.positionCount = 0;
            trailLine.useWorldSpace = true;

            Material material = new Material(Shader.Find("Sprites/Default"));
            material.color = Color.cyan;
            trailLine.material = material;
        }
    }

    private void AddTrailPoint(Vector3 position)
    {
        if (trailLine == null)
        {
            return;
        }

        Vector3 trailPosition = new Vector3(position.x, 0.12f, position.z);

        trailLine.positionCount += 1;
        trailLine.SetPosition(trailLine.positionCount - 1, trailPosition);
    }

    private void ClearTrail()
    {
        if (trailLine != null)
        {
            trailLine.positionCount = 0;
        }
    }

    private void RotateRobotByAction(string action)
    {
        if (string.IsNullOrEmpty(action))
        {
            return;
        }

        if (action == "GIRAR_DERECHA")
        {
            robot.Rotate(Vector3.up, 90f);
        }
        else if (action == "GIRAR_IZQUIERDA")
        {
            robot.Rotate(Vector3.up, -90f);
        }
    }

    private void ApplyRobotVisualState(MissionStep step)
    {
        Renderer renderer = robot.GetComponentInChildren<Renderer>();

        if (renderer == null)
        {
            return;
        }

        if (step.return_to_base_mode)
        {
            renderer.material.color = Color.blue;
            return;
        }

        if (step.escape_mode)
        {
            renderer.material.color = new Color(1f, 0.5f, 0f);
            return;
        }

        if (step.risk_level == "ALTO")
        {
            renderer.material.color = Color.red;
        }
        else if (step.risk_level == "MEDIO")
        {
            renderer.material.color = Color.yellow;
        }
        else
        {
            renderer.material.color = Color.green;
        }
    }

    private void SetupHudStyles()
    {
        hudStyle = new GUIStyle();
        hudStyle.fontSize = 20;
        hudStyle.normal.textColor = Color.white;

        titleStyle = new GUIStyle();
        titleStyle.fontSize = 26;
        titleStyle.fontStyle = FontStyle.Bold;
        titleStyle.normal.textColor = Color.white;

        modeStyle = new GUIStyle();
        modeStyle.fontSize = 20;
        modeStyle.fontStyle = FontStyle.Bold;
        modeStyle.normal.textColor = Color.cyan;
    }

    void OnGUI()
    {
        if (currentStep == null)
        {
            return;
        }

        GUI.Box(new Rect(15, 15, 470, 250), "");

        GUI.Label(new Rect(30, 25, 440, 30), "RescueTwin AI - Replay de misión", titleStyle);

        GUI.Label(new Rect(30, 65, 430, 25), "Step: " + currentStep.step, hudStyle);
        GUI.Label(new Rect(30, 90, 430, 25), "Posición: (" + currentStep.x + ", " + currentStep.y + ")", hudStyle);
        GUI.Label(new Rect(30, 115, 430, 25), "Acción: " + currentStep.action, hudStyle);
        GUI.Label(new Rect(30, 140, 430, 25), "Riesgo: " + currentStep.risk_level, hudStyle);
        GUI.Label(new Rect(30, 165, 430, 25), "Batería: " + currentStep.battery_level, hudStyle);

        string mode = "EXPLORACIÓN";

        if (currentStep.return_to_base_mode)
        {
            mode = "RETORNO A BASE";
        }
        else if (currentStep.escape_mode)
        {
            mode = "ESCAPE";
        }

        GUI.Label(new Rect(30, 195, 430, 25), "Modo: " + mode, modeStyle);

        GUI.Label(
            new Rect(30, 225, 430, 25),
            "Colores: verde=bajo | amarillo=medio | rojo=alto | azul=retorno | naranja=escape",
            hudStyle
        );
    }
}