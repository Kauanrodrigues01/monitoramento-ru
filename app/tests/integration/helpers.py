async def persist(session, *instances):
    for instance in instances:
        session.add(instance)
    await session.flush()
    for instance in instances:
        await session.refresh(instance)
    return instances if len(instances) > 1 else instances[0]
