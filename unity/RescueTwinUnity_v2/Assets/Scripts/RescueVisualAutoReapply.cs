using System.Collections;
using UnityEngine;

public class RescueVisualAutoReapply : MonoBehaviour
{
    [Header("Referencias")]
    public RescueTwinVisualPolish scenePolish;
    public RescueRobotVisualStable robotPolish;

    [Header("Configuración")]
    public float reapplyDelay = 0.35f;

    private Coroutine reapplyCoroutine;

    void Start()
    {
        AutoFindReferences();
        ScheduleReapply();
    }

    void Update()
    {
        if (DemoKeyPressed() || Input.GetKeyDown(KeyCode.R))
        {
            ScheduleReapply();
        }
    }

    private bool DemoKeyPressed()
    {
        return Input.GetKeyDown(KeyCode.Alpha1)
            || Input.GetKeyDown(KeyCode.Alpha2)
            || Input.GetKeyDown(KeyCode.Alpha3)
            || Input.GetKeyDown(KeyCode.Alpha4)
            || Input.GetKeyDown(KeyCode.Alpha5)
            || Input.GetKeyDown(KeyCode.Alpha6)
            || Input.GetKeyDown(KeyCode.Alpha7)
            || Input.GetKeyDown(KeyCode.Alpha8)
            || Input.GetKeyDown(KeyCode.Alpha9);
    }

    private void AutoFindReferences()
    {
        if (scenePolish == null)
        {
            scenePolish = FindAnyObjectByType<RescueTwinVisualPolish>();
        }

        if (robotPolish == null)
        {
            robotPolish = FindAnyObjectByType<RescueRobotVisualStable>();
        }
    }

    private void ScheduleReapply()
    {
        if (reapplyCoroutine != null)
        {
            StopCoroutine(reapplyCoroutine);
        }

        reapplyCoroutine = StartCoroutine(ReapplyAfterDelay());
    }

    private IEnumerator ReapplyAfterDelay()
    {
        yield return new WaitForSeconds(reapplyDelay);

        AutoFindReferences();

        if (scenePolish != null)
        {
            scenePolish.RebuildVisuals();
            Debug.Log("[RescueVisualAutoReapply] Visuales de escena reaplicados.");
        }
        else
        {
            Debug.LogWarning("[RescueVisualAutoReapply] No se encontró RescueTwinVisualPolish.");
        }

        if (robotPolish != null)
        {
            robotPolish.BuildOrRefresh();
            Debug.Log("[RescueVisualAutoReapply] Visual del robot reaplicado.");
        }
        else
        {
            Debug.LogWarning("[RescueVisualAutoReapply] No se encontró RescueRobotVisualStable.");
        }
    }
}