using System.Collections;
using UnityEngine;

public class RescueVisualAutoReapply : MonoBehaviour
{
    [Header("Referencias")]
    public RescueTwinVisualPolish scenePolish;
    public RescueRobotVisualStable robotPolish;

    [Header("Tiempo de espera")]
    public float reapplyDelay = 0.25f;

    private Coroutine reapplyRoutine;

    private void Start()
    {
        FindReferencesIfNeeded();
    }

    private void Update()
    {
        if (
            Input.GetKeyDown(KeyCode.Alpha1) ||
            Input.GetKeyDown(KeyCode.Alpha2) ||
            Input.GetKeyDown(KeyCode.R)
        )
        {
            ScheduleReapply();
        }
    }

    private void FindReferencesIfNeeded()
    {
        if (scenePolish == null)
            scenePolish = FindObjectOfType<RescueTwinVisualPolish>();

        if (robotPolish == null)
            robotPolish = FindObjectOfType<RescueRobotVisualStable>();
    }

    private void ScheduleReapply()
    {
        if (reapplyRoutine != null)
            StopCoroutine(reapplyRoutine);

        reapplyRoutine = StartCoroutine(ReapplyAfterDelay());
    }

    private IEnumerator ReapplyAfterDelay()
    {
        yield return new WaitForSeconds(reapplyDelay);

        FindReferencesIfNeeded();

        if (scenePolish != null)
        {
            scenePolish.RebuildVisuals();
        }

        yield return new WaitForSeconds(0.10f);

        if (robotPolish != null)
        {
            robotPolish.BuildOrRefresh();
        }

        Debug.Log("Visual polish reaplicado después de cambiar demo.");
    }
}